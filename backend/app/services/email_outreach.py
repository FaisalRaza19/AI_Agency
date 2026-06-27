import httpx
import uuid
from typing import Optional, List
from sqlalchemy import select
from app.config import settings
from app.database import async_session_maker
from app.models import SenderDomain

class ResilientEmailOutreachClient:
    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.base_url = "https://api.resend.com/emails"

    async def select_best_sender(self) -> SenderDomain:
        """
        Selects the best available sender domain out of PostgreSQL.
        Picks the active domain with the highest weight.
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(SenderDomain)
                .where(SenderDomain.is_active == True, SenderDomain.weight > 0)
                .order_by(SenderDomain.weight.desc(), SenderDomain.id.asc())
            )
            domains = result.scalars().all()
            
            if not domains:
                raise RuntimeError("CRITICAL: No active verified sender domains available in PostgreSQL registry.")
            
            # Select the top weighted domain (picks first)
            return domains[0]

    async def send_outreach_email(
        self, 
        recipient: str, 
        subject: str, 
        html_body: str,
        campaign_id: str
    ) -> str:
        """
        Sends an email via the Resend API, rotating domains dynamically based on weight indexes.
        Returns the unique Resend message ID.
        """
        sender = await self.select_best_sender()
        from_header = f"UABE Closer <{sender.from_email}>"

        if not self.api_key or self.api_key == "mock_key":
            mock_id = f"resend-evt-{uuid.uuid4()}"
            print(f"[EMAIL MOCK] Sending email via dynamic domain '{sender.domain}' ({sender.from_email}):")
            print(f"  To: {recipient}")
            print(f"  From: {from_header}")
            print(f"  Subject: {subject}")
            print(f"  Mock Resend ID: {mock_id}")
            return mock_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "from": from_header,
            "to": [recipient],
            "subject": subject,
            "html": html_body
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(self.base_url, headers=headers, json=payload, timeout=15.0)
                if res.status_code in [200, 201]:
                    data = res.json()
                    message_id = data.get("id")
                    print(f"Resend Email Sent successfully (ID: {message_id}) using domain '{sender.domain}'.")
                    return message_id
                else:
                    print(f"Resend API error {res.status_code}: {res.text}")
                    raise RuntimeError(f"Resend API error: {res.text}")
        except Exception as e:
            print(f"Exception during Resend email dispatch: {e}")
            raise

# Instantiate global resilient email client
email_outreach_client = ResilientEmailOutreachClient()
