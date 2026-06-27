import json
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from svix.webhooks import Webhook, WebhookVerificationError

from app.config import settings
from app.database import get_db
from app.services.redis_service import redis_service
from app.models import SenderDomain, Lead
from app.core.orchestrator import orchestrator

router = APIRouter(prefix="/email", tags=["Resend Email Webhooks"])

# Local in-memory fallback cache to ensure idempotency if Redis is down
processed_events_fallback = set()

@router.post("/webhook")
async def resend_email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    svix_id: Optional[str] = Header(None),
    svix_timestamp: Optional[str] = Header(None),
    svix_signature: Optional[str] = Header(None)
):
    """
    Exposes a secure webhook endpoint to receive and process Resend email status updates.
    Verifies Svix signature headers on the raw request body bytes and enforces event idempotency.
    """
    # 1. Capture pristine raw body bytes to prevent signature check failures due to formatting
    raw_body = await request.body()
    
    # 2. Signature verification logic
    signing_secret = settings.RESEND_WEBHOOK_SIGNING_SECRET
    
    # Verify signature only in production mode or if a secret is explicitly set
    if settings.ENVIRONMENT == "production" or (signing_secret and signing_secret != "mock_secret"):
        if not (svix_id and svix_timestamp and svix_signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Missing required Svix headers."
            )
            
        try:
            wh = Webhook(signing_secret)
            # Verify signature using raw bytes and headers
            wh.verify(raw_body, {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature
            })
        except WebhookVerificationError as e:
            print(f"Svix signature validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Invalid Svix cryptographic signature."
            )

    # 3. Strict Idempotency Protection: cache svix-id in Redis
    event_token = svix_id or request.headers.get("x-mock-svix-id")
    if event_token:
        cache_key = f"svix_event:{event_token}"
        already_processed = await redis_service.get_cache(cache_key)
        
        # If not found in Redis (or Redis is offline), check local fallback registry
        if not already_processed:
            already_processed = event_token in processed_events_fallback
            
        if already_processed:
            print(f"Svix Idempotency: Ignoring duplicate event '{event_token}'.")
            return {"status": "ignored", "reason": "duplicate_webhook"}
            
        # Cache token for 24 hours to prevent duplicate replays
        success = await redis_service.set_cache(cache_key, "processed", expire=86400)
        if not success:
            # If Redis is offline/error, log to local set
            processed_events_fallback.add(event_token)

    # 4. Parse payload data
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    event_type = payload.get("type")
    event_data = payload.get("data", {})
    
    sender_email = event_data.get("from")
    recipient_list = event_data.get("to", [])
    recipient = recipient_list[0] if recipient_list else None

    # Parse sending domain
    sender_domain = ""
    if sender_email and "@" in sender_email:
        sender_domain = sender_email.split("@")[-1].strip()

    # 5. Handle bounce or complaint events to demote sending domains
    if event_type in ["email.bounced", "email.complained"]:
        print(f"Email outreach exception detected: {event_type} on sender domain '{sender_domain}'")
        
        # Demote sending domain weight index in PostgreSQL
        if sender_domain:
            domain_res = await db.execute(select(SenderDomain).where(SenderDomain.domain == sender_domain))
            domain_record = domain_res.scalar_one_or_none()
            if domain_record:
                # Reduce weight index by 50% or disable if it hits zero
                old_weight = domain_record.weight
                new_weight = max(0, old_weight - 50)
                domain_record.weight = new_weight
                if new_weight == 0:
                    domain_record.is_active = False
                await db.commit()
                
                await orchestrator.log_agent_action(
                    campaign_id=None,
                    agent_name="deal_closer",
                    message=(
                        f"Resend Webhook: Domain '{sender_domain}' hit {event_type}. "
                        f"Weight reduced from {old_weight} to {new_weight}. "
                        f"Active state: {domain_record.is_active}"
                    ),
                    log_level="warning"
                )

        # Update recipient Lead outreach status
        if recipient:
            lead_res = await db.execute(select(Lead).where(Lead.email == recipient))
            lead_record = lead_res.scalar_one_or_none()
            if lead_record:
                status_mapping = {
                    "email.bounced": "bounced",
                    "email.complained": "declined"
                }
                lead_record.outreach_status = status_mapping.get(event_type, "pending")
                await db.commit()

    return {"status": "processed", "event_id": event_token}
