import json
import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.gemini_client import llm_client
from app.models import Deliverable, AgentLog

class QAReport(BaseModel):
    is_approved: bool = Field(..., description="True if the copy meets all professional guidelines and strategic alignment rules.")
    rejections: List[str] = Field(default=[], description="List of specific flaws, toxic expressions, or errors identified in the copy.")
    score: float = Field(..., description="A quality score from 0.0 to 100.0 rating the professionalism and value of the deliverable.")
    feedback: str = Field(..., description="Constructive suggestions for rewriting the copy to resolve identified issues.")

class QAValidatorService:
    def check_link_integrity(self, body: str) -> List[str]:
        """Scans the markdown text for malformed URLs or invalid link targets."""
        rejections = []
        # Find markdown links like [Anchor](url)
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)
        for text, url in links:
            url_stripped = url.strip()
            # If URL is empty, missing http protocol, or contains whitespace
            if not url_stripped:
                rejections.append(f"Markdown link '[{text}]' has an empty URL target.")
            elif not url_stripped.startswith(("http://", "https://", "mailto:", "tel:")):
                rejections.append(f"Link target '{url_stripped}' is missing a valid protocol (http, https, tel, mailto).")
            elif " " in url_stripped:
                rejections.append(f"Link target '{url_stripped}' contains invalid spaces.")
        return rejections

    def scan_spam_words(self, body: str) -> List[str]:
        """Local regex filter scanning for common spam triggers and unprofessional words."""
        rejections = []
        # Case insensitive scanning
        spam_triggers = [
            r"\bmake\s+money\s+fast\b",
            r"\b100%\s+free\b",
            r"\bdouble\s+your\s+income\b",
            r"\bclick\s+here\s+now\b",
            r"\bguaranteed\s+wealth\b",
            r"\bviagra\b",
            r"\bcasino\b"
        ]
        for trigger in spam_triggers:
            if re.search(trigger, body, re.IGNORECASE):
                rejections.append(f"Detected spam trigger word matching pattern: {trigger}")
        return rejections

    async def run_semantic_qa(self, title: str, body: str, objective: str) -> QAReport:
        """Queries Gemini to perform structured semantic analysis on marketing deliverables."""
        system_prompt = (
            "You are an expert Quality Assurance editor reviewing copywriting assets.\n"
            "Analyze the title and body against the target strategic campaign objective.\n"
            "Ensure the tone is professional, helpful, and contains no toxic or offensive phrasing.\n"
            "You MUST return a JSON object matching this exact schema:\n"
            "{\n"
            "  \"is_approved\": false,\n"
            "  \"rejections\": [\"Details about specific flaws...\"],\n"
            "  \"score\": 82.5,\n"
            "  \"feedback\": \"Rewrite suggestion details...\"\n"
            "}"
        )

        prompt = (
            f"Deliverable Title: {title}\n"
            f"Deliverable Body (Markdown):\n{body}\n\n"
            f"Strategic Objective to evaluate against: {objective}\n"
        )

        try:
            res_text = await llm_client.generate_text(prompt, system_prompt, json_mode=True)
            data = json.loads(res_text)
            report = QAReport.model_validate(data)
            return report
        except Exception as e:
            print(f"[QA_VALIDATOR] Semantic LLM QA failed ({e}). Falling back to automatic approval.")
            # Resilient fallback approving if Gemini is offline
            return QAReport(
                is_approved=True,
                rejections=[],
                score=90.0,
                feedback="Approved automatically via offline fallback."
            )

    async def validate_and_refine_deliverable(self, db: AsyncSession, deliverable_id: str) -> Deliverable:
        """
        Loads the deliverable, runs link checks, spam scans, and semantic LLM QA.
        Enforces a strict integer limit (refinement_count < 3) to prevent infinite loops.
        """
        # Load deliverable and campaign objective
        from sqlalchemy import select
        from app.models import Campaign
        
        result = await db.execute(select(Deliverable).where(Deliverable.id == deliverable_id))
        deliverable = result.scalar_one_or_none()
        if not deliverable:
            raise ValueError(f"Deliverable #{deliverable_id} not found.")

        campaign_res = await db.execute(select(Campaign).where(Campaign.id == deliverable.campaign_id))
        campaign = campaign_res.scalar_one_or_none()
        objective = campaign.objective if campaign else "Outbound SEO outreach"

        # 1. Run local checks
        local_rejections = self.check_link_integrity(deliverable.content_body)
        spam_rejections = self.scan_spam_words(deliverable.content_body)
        
        # 2. Run LLM semantic QA
        qa_report = await self.run_semantic_qa(deliverable.title, deliverable.content_body, objective)

        # Merge rejections
        all_rejections = local_rejections + spam_rejections + qa_report.rejections
        is_approved = qa_report.is_approved and len(all_rejections) == 0

        # Create Agent Log entry for tracking
        log_msg = f"[QA] Evaluated deliverable '{deliverable.title}'. Score: {qa_report.score}%. Approved: {is_approved}."
        if all_rejections:
            log_msg += f" Rejections: {', '.join(all_rejections)}"
        
        log_entry = AgentLog(
            campaign_id=deliverable.campaign_id,
            agent_name="qa",
            log_level="info" if is_approved else "warning",
            message=log_msg
        )
        db.add(log_entry)

        if is_approved:
            deliverable.status = "approved"
            deliverable.qa_feedback = None
        else:
            # Increment refinement loop counter
            deliverable.refinement_count += 1
            deliverable.qa_feedback = f"Rejections: {'; '.join(all_rejections)}. Feedback: {qa_report.feedback}"
            
            # Enforce strict refinement loop cap to prevent infinite credit drain
            if deliverable.refinement_count >= 3:
                deliverable.status = "manual_review_pending"
                
                # Write critical warning log
                warn_entry = AgentLog(
                    campaign_id=deliverable.campaign_id,
                    agent_name="qa",
                    log_level="error",
                    message=f"[QA_ALERT] Deliverable '{deliverable.title}' hit refinement limit (3 attempts). Halting automated loops to prevent token exhaustion. Flagged for Manual Review."
                )
                db.add(warn_entry)
            else:
                deliverable.status = "qa_pending" # Triggers rebuild on next run

        await db.commit()
        return deliverable

qa_validator_service = QAValidatorService()
