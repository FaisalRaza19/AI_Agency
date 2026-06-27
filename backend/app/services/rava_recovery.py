import json
from typing import Optional, Dict, Any
import httpx
from app.config import settings
from app.services.redis_service import redis_service
from app.database import async_session_maker
from app.models import Lead

class RAVARecoveryManager:
    def __init__(self):
        self.session_prefix = "rava_session"

    async def send_twilio_recovery_sms(self, phone: str, recovery_link: str) -> bool:
        """Sends an out-of-band recovery link to the client's phone via Twilio SMS API."""
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
            print("WARNING: Twilio credentials are not set. Skipping recovery SMS.")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        data = {
            "To": phone,
            "From": settings.TWILIO_FROM_NUMBER,
            "Body": f"Looks like our call dropped! Tap here to re-enter our live sync room or continue over text: {recovery_link}"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, auth=auth, data=data, timeout=10.0)
                if response.status_code in [200, 201]:
                    print(f"Twilio SMS recovery notification sent successfully to {phone}.")
                    return True
                else:
                    print(f"Twilio API returned error {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            print(f"Exception while calling Twilio SMS recovery: {e}")
            return False

    async def handle_disconnect(
        self, 
        campaign_id: str, 
        lead_id: str, 
        session_state: Dict[str, Any]
    ) -> None:
        """
        Protects the live session state inside Upstash Redis for a 5-minute grace period.
        Fires an asynchronous out-of-band Twilio SMS notification with a recovery URL.
        """
        cache_key = f"{self.session_prefix}:{lead_id}"
        serialized_state = json.dumps(session_state)
        
        # Save state inside Redis cache with a 5-minute (300 seconds) expiration TTL
        await redis_service.set_cache(cache_key, serialized_state, expire=300)
        print(f"Protected live RAVA session for lead '{lead_id}' in Redis (300s grace period).")

        # Fetch lead phone number from PostgreSQL
        async with async_session_maker() as session:
            lead = await session.get(Lead, lead_id)
            if lead and lead.phone:
                recovery_link = f"https://uabe.com/call-recovery/{lead_id}"
                # Fire recovery SMS out-of-band
                await self.send_twilio_recovery_sms(lead.phone, recovery_link)

    async def handle_reconnect(self, lead_id: str, new_webrtc_call_id: str) -> Optional[Dict[str, Any]]:
        """
        Checks Redis for a suspended grace-period session.
        If found, retrieves the context state and maps it back to resume RAVA cleanly.
        """
        cache_key = f"{self.session_prefix}:{lead_id}"
        cached_state_str = await redis_service.get_cache(cache_key)

        if not cached_state_str:
            print(f"RAVA Reconnect failed: Grace period expired or session not found for lead '{lead_id}'.")
            return None

        # Parse context state
        session_state = json.loads(cached_state_str)
        # Update session with the new WebRTC Call ID mapping
        session_state["webrtc_call_id"] = new_webrtc_call_id
        session_state["reconnected"] = True
        
        # Keep state updated in Redis in case of subsequent disconnects
        await redis_service.set_cache(cache_key, json.dumps(session_state), expire=300)
        print(f"RAVA Reconnected: Successfully mapped new Call ID '{new_webrtc_call_id}' to lead '{lead_id}'.")
        return session_state

# Instantiate global recovery manager
rava_recovery_manager = RAVARecoveryManager()
