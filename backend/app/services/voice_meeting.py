import json
from typing import Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.core.gemini_client import llm_client

class CloserAnalysis(BaseModel):
    is_agreed: bool = Field(..., description="True if the prospect explicitly agreed to sign the contract, False otherwise.")
    agreed_price: float = Field(..., description="The negotiated monthly subscription price in USD (e.g. 1500.00). Defaults to 0.0 if not agreed.")
    summary: str = Field(..., description="A brief summary of the objections, key terms, and the call result.")

class VoiceMeetingService:
    async def simulate_closer_call(self, lead_name: str, company: str, objective: str) -> Tuple[str, CloserAnalysis]:
        """
        Generates a simulated voice call transcript between the AI closer agent and the lead.
        Then queries Gemini to extract deterministic agreement and pricing details.
        """
        # 1. Generate a mock closer call transcript
        transcript = f"""
Closer Agent: Hello, is this {lead_name} from {company}?
Prospect ({lead_name}): Yes, speaking. Who is this?
Closer Agent: I'm calling from the outreach team. We've been analyzing {company}'s online pipeline and noticed that your search presence in Miami has some quick wins. We can help you rank on the first page of Google for search queries related to {objective}.
Prospect ({lead_name}): Oh, we've had agencies pitch us before. It's usually a lot of money and no results. What's your pricing model?
Closer Agent: We align our incentives with your success. We don't charge large upfront retainers. We're looking at a monthly model of $2,500.00 which includes the complete content generation, local SEO optimization, and outreach campaign.
Prospect ({lead_name}): $2,500 is a bit steep for our current budget. Could we do $1,800 for the first three months to test the ROI?
Closer Agent: I understand. If we start at $1,800.00/month, we can run the local optimization first, then expand as you see leads come in. Let's agree to lock in $1,800.00 for the pilot phase. I'll send over the contract and Stripe checkout page. Does that work?
Prospect ({lead_name}): Yes, that sounds fair. Let's do $1,800.00/month. Send it over and I'll sign it today.
Closer Agent: Excellent. Setting up the invoice and contract now. Have a great day!
        """

        # 2. Structured LLM prompt
        system_prompt = (
            "Analyze the voice call transcript and extract the negotiation result.\n"
            "You MUST return a JSON object matching this exact schema:\n"
            "{\n"
            "  \"is_agreed\": true,\n"
            "  \"agreed_price\": 1800.0,\n"
            "  \"summary\": \"Brief details about Miami Dentist pilot phase agreement...\"\n"
            "}"
        )

        prompt = f"Objective: {objective}\nTranscript:\n{transcript}"

        try:
            res_text = await llm_client.generate_text(prompt, system_prompt, json_mode=True)
            # Safe JSON load and Pydantic validation to guarantee deterministic outputs
            data = json.loads(res_text)
            analysis = CloserAnalysis.model_validate(data)
            return transcript, analysis
        except Exception as e:
            print(f"[VOICE_MEETING] Structured LLM parsing failed ({e}). Falling back to static values.")
            # Resilient fallback matching the transcript terms
            fallback = CloserAnalysis(
                is_agreed=True,
                agreed_price=1800.0,
                summary="Client agreed to pilot Miami SEO services for $1,800.00/month."
            )
            return transcript, fallback

voice_meeting_service = VoiceMeetingService()
