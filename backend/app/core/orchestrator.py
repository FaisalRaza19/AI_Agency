import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, update
from app.database import async_session_maker
from app.models import Campaign, CampaignWallet, AgentLog, Lead
from app.core.gemini_client import llm_client
from app.services.redis_service import redis_service
from app.services.research import research_service
from app.services.verifier import verifier_client

class ExecutiveBrainOrchestrator:
    def __init__(self):
        # Operational agent roles in the system
        self.roles = {
            "researcher": "deep_research",
            "copywriter": "copywriter",
            "closer": "deal_closer",
            "pm": "project_manager",
            "builder": "worker_builder",
            "qa": "quality_assurance"
        }

    async def log_agent_action(
        self, 
        campaign_id: str, 
        agent_name: str, 
        message: str, 
        log_level: str = "info", 
        is_reflection: bool = False
    ) -> None:
        """Helper utility to write execution logs into the central database."""
        async with async_session_maker() as session:
            log_entry = AgentLog(
                campaign_id=campaign_id,
                agent_name=agent_name,
                log_level=log_level,
                message=message,
                is_reflection=is_reflection
            )
            session.add(log_entry)
            await session.commit()
            print(f"[{agent_name.upper()}][{log_level.upper()}] Campaign {campaign_id}: {message}")

    async def execute_llm_call(
        self, 
        campaign_id: str, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        json_mode: bool = False,
        agent_name: str = "executive"
    ) -> str:
        """
        ROI-Aware Inline Budget Interceptor.
        Enforces budget caps INLINE before routing any prompt to the LLM Client.
        If budget threshold is hit, freezes COLD campaigns while letting active negotiations bypass.
        """
        async with async_session_maker() as session:
            # 1. Fetch Campaign and Wallet details
            wallet_res = await session.execute(
                select(CampaignWallet).where(CampaignWallet.campaign_id == campaign_id)
            )
            wallet = wallet_res.scalar_one_or_none()
            
            if not wallet:
                # No budget bounds specified, execute model directly
                return await llm_client.generate_text(prompt, system_instruction, json_mode)

            if wallet.is_liquidated:
                raise RuntimeError(f"Execution blocked: Campaign {campaign_id} has been liquidated.")

            # 2. Check usage ratio
            usage_ratio = wallet.cost_spent / wallet.budget if wallet.budget > 0 else 0
            
            if usage_ratio >= 0.75:
                # 3. Check for active contract negotiations or live negotiations
                leads_res = await session.execute(
                    select(Lead).where(
                        Lead.campaign_id == campaign_id,
                        Lead.outreach_status.in_(["IN_LIVE_NEGOTIATION", "CONTRACT_PENDING"])
                    )
                )
                active_negotiation_leads = leads_res.scalars().all()
                
                if active_negotiation_leads:
                    # Bypassing the freeze - lead is active. Transition campaign to Elevated Monitoring state
                    campaign_res = await session.execute(
                        select(Campaign).where(Campaign.id == campaign_id)
                    )
                    campaign = campaign_res.scalar_one()
                    if campaign.status != "elevated_monitoring":
                        campaign.status = "elevated_monitoring"
                        await session.commit()
                        
                    await self.log_agent_action(
                        campaign_id=campaign_id,
                        agent_name="executive",
                        message=(
                            f"ROI Interceptor: Campaign has burned {usage_ratio * 100:.1f}% of budget "
                            f"(${wallet.cost_spent:.2f}/${wallet.budget:.2f}). Bypassing kill-switch due to "
                            f"{len(active_negotiation_leads)} active negotiation leads. Elevated Monitoring State activated."
                        ),
                        log_level="warning"
                    )
                else:
                    # No active negotiations (leads are COLD or inactive) - Halt loop and freeze Campaign
                    wallet.is_liquidated = True
                    
                    campaign_res = await session.execute(
                        select(Campaign).where(Campaign.id == campaign_id)
                    )
                    campaign = campaign_res.scalar_one()
                    campaign.status = "interrupted"
                    await session.commit()
                    
                    await self.log_agent_action(
                        campaign_id=campaign_id,
                        agent_name="executive",
                        message=(
                            f"ROI Interceptor: Campaign has burned {usage_ratio * 100:.1f}% of budget "
                            f"(${wallet.cost_spent:.2f}/${wallet.budget:.2f}) with zero active leads. Freezing execution."
                        ),
                        log_level="error"
                    )
                    raise RuntimeError(f"Campaign {campaign_id} budget limit frozen: ROI threshold exceeded with cold leads.")

        # 4. Perform the text generation
        response = await llm_client.generate_text(prompt, system_instruction, json_mode)

        # 5. Estimate token usage cost and update the wallet
        input_tokens = (len(prompt) + len(system_instruction or "")) // 4
        output_tokens = len(response) // 4
        
        # Estimate cost: Use Claude pricing ($3/1M input, $15/1M output) as worst-case budget tracking
        estimated_cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

        async with async_session_maker() as session:
            db_wallet = await session.get(CampaignWallet, campaign_id)
            if db_wallet:
                db_wallet.cost_spent += estimated_cost
                db_wallet.last_checked = datetime.now(timezone.utc)
                await session.commit()

        return response

    async def parse_objective_to_milestones(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Interprets the campaign objective using LLM reasoning and compiles
        the strategic execution milestones.
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")

        system_prompt = (
            "You are the Executive PM Brain of the Universal Autonomous Business Engine (UABE).\n"
            "Analyze the business objective and return a structured JSON list of milestones.\n"
            "Return ONLY a raw JSON array matching this format: \n"
            "[\n"
            "  {\"id\": 1, \"milestone\": \"milestone_name\", \"agent\": \"assigned_agent_name\", \"action\": \"description\"}\n"
            "]"
        )
        
        prompt = f"Objective to analyze: {campaign.objective}"
        
        await self.log_agent_action(
            campaign_id=campaign_id,
            agent_name="executive",
            message="Analyzing campaign objective and generating task milestones..."
        )

        try:
            # Generate structured response using the inline budget interceptor wrapper
            response_text = await self.execute_llm_call(
                campaign_id=campaign_id,
                prompt=prompt,
                system_instruction=system_prompt,
                json_mode=True,
                agent_name="executive"
            )
            milestones = json.loads(response_text)
            
            await self.log_agent_action(
                campaign_id=campaign_id,
                agent_name="executive",
                message=f"Milestone roadmap generated successfully. Total steps: {len(milestones)}"
            )
            return milestones
        except Exception as e:
            await self.log_agent_action(
                campaign_id=campaign_id,
                agent_name="executive",
                message=f"Failed to generate milestone plan: {e}",
                log_level="error"
            )
            return []

    async def check_budget_gate(self, campaign_id: str) -> bool:
        """
        Check if the campaign has remaining budget to continue execution.
        Returns True if budget is safe, False otherwise.
        """
        async with async_session_maker() as session:
            wallet_res = await session.execute(
                select(CampaignWallet).where(CampaignWallet.campaign_id == campaign_id)
            )
            wallet = wallet_res.scalar_one_or_none()
            if not wallet:
                return True
                
            if wallet.is_liquidated:
                return False
                
            if wallet.cost_spent >= wallet.budget:
                wallet.is_liquidated = True
                campaign_res = await session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                )
                campaign = campaign_res.scalar_one_or_none()
                if campaign:
                    campaign.status = "interrupted"
                await session.commit()
                
                await self.log_agent_action(
                    campaign_id=campaign_id,
                    agent_name="executive",
                    message=f"Budget Guardrail: Campaign frozen. Spent ${wallet.cost_spent:.2f} of ${wallet.budget:.2f}.",
                    log_level="error"
                )
                return False
                
            return True

    async def route_execution_step(self, campaign_id: str, step_data: Dict[str, Any]) -> None:
        """
        Core router executing the specific node task within the state machine.
        Redlock guards prevent concurrency collisions.
        """
        lock_name = f"campaign_execution:{campaign_id}"
        agent_role = step_data.get("agent", "executive").lower()
        
        try:
            # Use Redlock context wrapper to execute step safely
            async with redis_service.lock(lock_name, lock_timeout=60.0):
                await self.log_agent_action(
                    campaign_id=campaign_id,
                    agent_name=agent_role,
                    message=f"Executing Milestone #{step_data.get('id')}: {step_data.get('milestone')}..."
                )
                
                if agent_role in ["deep_research", "researcher"]:
                    # Run Deep Research spoke
                    async with async_session_maker() as session:
                        campaign_res = await session.execute(
                            select(Campaign).where(Campaign.id == campaign_id)
                        )
                        campaign = campaign_res.scalar_one_or_none()
                        if not campaign:
                            raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")
                            
                    extracted_leads = await research_service.gather_leads_from_objective(
                        campaign.objective, 
                        campaign_id
                    )
                    
                    added_count = 0
                    cleansed_count = 0
                    
                    async with async_session_maker() as session:
                        for lead in extracted_leads:
                            email = lead.get("email")
                            if not email:
                                continue
                                
                            # Check if duplicate in current campaign
                            exists_res = await session.execute(
                                select(Lead).where(
                                    Lead.campaign_id == campaign_id,
                                    Lead.email == email
                                )
                            )
                            if exists_res.scalar_one_or_none():
                                continue
                                
                            # Run MillionVerifier check
                            verification_result = await verifier_client.verify_email(email)
                            if verification_result in ["invalid", "disposable"]:
                                cleansed_count += 1
                                await self.log_agent_action(
                                    campaign_id=campaign_id,
                                    agent_name="deep_research",
                                    message=f"Pre-flight cleansing: Dropped lead '{email}' due to validation state '{verification_result}'.",
                                    log_level="warning"
                                )
                                continue
                                
                            # Save valid lead
                            db_lead = Lead(
                                campaign_id=campaign_id,
                                email=email,
                                first_name=lead.get("first_name"),
                                last_name=lead.get("last_name"),
                                company=lead.get("company"),
                                phone=lead.get("phone"),
                                qualification_score=lead.get("qualification_score", 0.0),
                                verification_status="verified" if verification_result == "ok" else "catch_all" if verification_result == "catchall" else "unknown"
                            )
                            session.add(db_lead)
                            added_count += 1
                        await session.commit()
                        
                    await self.log_agent_action(
                        campaign_id=campaign_id,
                        agent_name="deep_research",
                        message=f"Deep Research complete. Added {added_count} leads, filtered {cleansed_count} invalid/disposable leads."
                    )
                elif agent_role in ["copywriter", "builder", "worker_builder"]:
                    # Spawns Worker/Copywriter to write content draft
                    from app.services.content_builder import content_builder_service
                    from app.models import Deliverable
                    
                    async with async_session_maker() as session:
                        # Find draft deliverables for campaign
                        result = await session.execute(
                            select(Deliverable).where(
                                Deliverable.campaign_id == campaign_id,
                                Deliverable.status == "draft"
                            )
                        )
                        drafts = result.scalars().all()
                        
                        if not drafts:
                            # Generate a default email template draft if none exists
                            deliverable = Deliverable(
                                campaign_id=campaign_id,
                                title=f"{campaign_id} Target Outreach",
                                content_type="email",
                                content_body="Pending compilation",
                                status="draft"
                            )
                            session.add(deliverable)
                            await session.commit()
                            await session.refresh(deliverable)
                            drafts = [deliverable]

                        for d in drafts:
                            await self.log_agent_action(
                                campaign_id=campaign_id,
                                agent_name="worker_builder",
                                message=f"Worker Spoke: Generating content assets for deliverable '{d.title}'..."
                            )
                            # Generate copy
                            generated = await content_builder_service.generate_deliverable(
                                company="Prospect Client",
                                content_type=d.content_type,
                                objective=f"Campaign ID: {campaign_id}"
                            )
                            d.title = generated.title
                            d.content_body = generated.body
                            d.status = "qa_pending"
                            session.add(d)
                            await session.commit()
                            
                            await self.log_agent_action(
                                campaign_id=campaign_id,
                                agent_name="worker_builder",
                                message=f"Worker Spoke: Compiled content for '{d.title}'. Submitting to Manager QA."
                            )

                elif agent_role in ["qa", "quality_assurance", "manager"]:
                    # Spawns Manager / QA reviewer to audit assets
                    from app.services.qa_validator import qa_validator_service
                    from app.models import Deliverable
                    
                    async with async_session_maker() as session:
                        result = await session.execute(
                            select(Deliverable).where(
                                Deliverable.campaign_id == campaign_id,
                                Deliverable.status == "qa_pending"
                            )
                        )
                        pending_assets = result.scalars().all()
                        
                        if not pending_assets:
                            await self.log_agent_action(
                                campaign_id=campaign_id,
                                agent_name="quality_assurance",
                                message="Manager Spoke: No pending assets found in QA registry queue.",
                                log_level="warning"
                            )
                        else:
                            for d in pending_assets:
                                await self.log_agent_action(
                                    campaign_id=campaign_id,
                                    agent_name="quality_assurance",
                                    message=f"Manager Spoke: Auditing deliverable '{d.title}' against client specifications..."
                                )
                                # Validate
                                validated = await qa_validator_service.validate_and_refine_deliverable(session, d.id)
                                await session.refresh(d)
                                
                                if d.status == "approved":
                                    await self.log_agent_action(
                                        campaign_id=campaign_id,
                                        agent_name="quality_assurance",
                                        message=f"Manager Spoke: Asset '{d.title}' successfully approved for delivery!"
                                    )
                                else:
                                    # Rejected (sent back to worker)
                                    await self.log_agent_action(
                                        campaign_id=campaign_id,
                                        agent_name="quality_assurance",
                                        message=f"Manager Spoke: Asset '{d.title}' rejected due to validation failure. Redirecting back to worker.",
                                        log_level="warning"
                                    )

                elif agent_role in ["pm", "project_manager"]:
                    # PM splits campaign objective into structured deliverables skeleton
                    from app.models import Deliverable
                    async with async_session_maker() as session:
                        # Generate task skeleton
                        d1 = Deliverable(
                            campaign_id=campaign_id,
                            title="Draft Email Outreach Copy",
                            content_type="email",
                            content_body="Task assigned to worker.",
                            status="draft"
                        )
                        d2 = Deliverable(
                            campaign_id=campaign_id,
                            title="Draft Marketing Ad Copy",
                            content_type="ad_copy",
                            content_body="Task assigned to worker.",
                            status="draft"
                        )
                        session.add(d1)
                        session.add(d2)
                        await session.commit()
                        
                        await self.log_agent_action(
                            campaign_id=campaign_id,
                            agent_name="project_manager",
                            message="PM Spoke: Split objective into 2 deliverables tasks and queued them for Workers."
                        )

                elif agent_role in ["closer", "deal_closer"]:
                    # Closer Bot handles negotiation simulations and updates lead status
                    from app.models import Lead
                    async with async_session_maker() as session:
                        leads_res = await session.execute(
                            select(Lead).where(
                                Lead.campaign_id == campaign_id,
                                Lead.outreach_status.in_(["pending", "email_sent", "replied"])
                            )
                        )
                        leads = leads_res.scalars().all()
                        for l in leads:
                            l.outreach_status = "closed_won"
                            session.add(l)
                        await session.commit()
                        
                        await self.log_agent_action(
                            campaign_id=campaign_id,
                            agent_name="deal_closer",
                            message=f"Closer Bot: Closed deals successfully for {len(leads)} campaign prospects."
                        )
                else:
                    # Fallback/mock processing for other spokes
                    await asyncio.sleep(0.5)
                
                await self.log_agent_action(
                    campaign_id=campaign_id,
                    agent_name=agent_role,
                    message=f"Completed Milestone #{step_data.get('id')} safely."
                )
        except TimeoutError:
            await self.log_agent_action(
                campaign_id=campaign_id,
                agent_name="executive",
                message=f"Execution lock timeout for step {step_data.get('id')}. Another agent is active.",
                log_level="warning"
            )
        except Exception as e:
            await self.log_agent_action(
                campaign_id=campaign_id,
                agent_name="executive",
                message=f"Error executing step {step_data.get('id')}: {e}",
                log_level="error"
            )

# Instantiate global orchestrator
orchestrator = ExecutiveBrainOrchestrator()
