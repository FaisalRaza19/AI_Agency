import httpx
from typing import List, Dict, Any
from app.config import settings
from app.models import Lead

class MillionVerifierClient:
    def __init__(self):
        self.api_key = settings.MILLIONVERIFIER_API_KEY
        self.base_url = "https://api.millionverifier.com/v3/"

    async def verify_email(self, email: str) -> str:
        """
        Queries MillionVerifier API to determine email validity.
        Returns one of: 'ok', 'invalid', 'disposable', 'catchall', 'unknown'.
        """
        # If API key is not configured (e.g. dev/testing), fallback to basic pattern check
        if not self.api_key or self.api_key == "mock_key":
            # For testing: mock certain domains
            domain = email.split("@")[-1].lower() if "@" in email else ""
            if domain in ["disposable.com", "tempmail.com", "trashmail.com"]:
                return "disposable"
            if "invalid" in email.lower() or not domain:
                return "invalid"
            return "ok"

        params = {
            "api": self.api_key,
            "email": email,
            "timeout": 15
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(self.base_url, params=params, timeout=20.0)
                if res.status_code == 200:
                    data = res.json()
                    # MillionVerifier returns result code in 'result' (e.g. 'ok', 'disposable', 'invalid')
                    result = data.get("result", "unknown")
                    print(f"MillionVerifier checked '{email}': result={result}")
                    return result
                else:
                    print(f"MillionVerifier API error {res.status_code}: {res.text}")
                    return "unknown"
        except Exception as e:
            print(f"Exception during MillionVerifier query for '{email}': {e}")
            return "unknown"

    async def screen_leads_list(self, leads: List[Lead]) -> List[Lead]:
        """
        Pre-flight list validation gate.
        Intercepts lead lists and drops any email flagged as 'invalid' or 'disposable'
        to keep campaign bounce rates strictly under 2%.
        """
        screened_leads = []
        for lead in leads:
            status = await self.verify_email(lead.email)
            if status == "ok":
                screened_leads.append(lead)
            else:
                print(f"Pre-flight cleansing: Dropping lead '{lead.email}' due to validation state '{status}'.")
        return screened_leads

# Instantiate global verification spoke client
verifier_client = MillionVerifierClient()
