import json
import uuid
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from app.core.gemini_client import llm_client

class GeneratedContent(BaseModel):
    title: str = Field(..., description="The title or subject line of the marketing deliverable.")
    body: str = Field(..., description="The main copy of the deliverable written in clean markdown format.")

class ContentBuilderService:
    async def generate_deliverable(
        self,
        company: str,
        content_type: str,
        objective: str
    ) -> GeneratedContent:
        """
        Dynamically generates high-conversion marketing copy tailored to the client's business objective.
        Utilizes Gemini Structured JSON mode to guarantee clean parsing.
        """
        system_prompt = (
            "You are an elite marketing copywriter.\n"
            "Generate professional, high-converting copy based on the client's business profile.\n"
            "You MUST return a JSON object with 'title' (string) and 'body' (markdown string) keys.\n"
            "Ensure the markdown body is detailed and professional."
        )

        prompt = (
            f"Client Company Name: {company}\n"
            f"Content Type requested: {content_type} (e.g. email outreach, blog post, social ad copy)\n"
            f"Strategic Business Objective: {objective}\n"
        )

        try:
            res_text = await llm_client.generate_text(prompt, system_prompt, json_mode=True)
            data = json.loads(res_text)
            content = GeneratedContent.model_validate(data)
            return content
        except Exception as e:
            print(f"[CONTENT_BUILDER] Structured LLM generation failed ({e}). Returning fallback copy.")
            # Resilient fallback
            fallback_title = f"{company} Local Search Campaign Guide"
            fallback_body = (
                f"# Strategic SEO Report for {company}\n\n"
                f"We have compiled a localized marketing blueprint to address your core objective: *{objective}*.\n\n"
                "### Core Action Items:\n"
                "1. Optimize local business directory citations.\n"
                "2. Synthesize high-intent search query content.\n"
                "3. Align outreach email workflows with localized metrics."
            )
            return GeneratedContent(title=fallback_title, body=fallback_body)

    def generate_dalle_image_url(self) -> str:
        """Generates a structured mock DALL-E image URL asset link for ad copy or blog graphics."""
        asset_id = str(uuid.uuid4())
        return f"https://images.uabe.com/generated/{asset_id}.png"

content_builder_service = ContentBuilderService()
