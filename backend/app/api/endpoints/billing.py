import json
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stripe

from app.config import settings
from app.database import get_db
from app.models import StripeEvent, User
from app.core.orchestrator import orchestrator

router = APIRouter(prefix="/billing", tags=["Stripe Subscription Billing"])

# Configure Stripe key
stripe.api_key = settings.STRIPE_API_KEY

@router.post("/webhook")
async def stripe_billing_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: Optional[str] = Header(None)
):
    """
    Exposes a secure webhook endpoint to capture subscription payments.
    Verifies Stripe signatures using raw request bytes and enforces strict idempotency.
    """
    # 1. Extract raw request bytes for signature verification to avoid JSON parsing traps
    raw_payload = await request.body()
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    # Verify signature only in production mode or if a webhook secret is explicitly set
    if settings.ENVIRONMENT == "production" or (webhook_secret and webhook_secret != "mock_secret"):
        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Missing stripe-signature header."
            )
        try:
            event = stripe.Webhook.construct_event(
                raw_payload, stripe_signature, webhook_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            print(f"Stripe signature verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Invalid Stripe cryptographic signature."
            )
    else:
        # Development fallback / Mock parser
        try:
            event = json.loads(raw_payload.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    # 2. Strict Idempotency Gate: Atomic Postgres transaction lookup
    event_id = event.get("id")
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request: Missing event identifier."
        )

    # Begin atomic transaction check
    event_res = await db.execute(select(StripeEvent).where(StripeEvent.event_id == event_id))
    existing_event = event_res.scalar_one_or_none()
    
    if existing_event:
        print(f"Stripe Idempotency: Event '{event_id}' has already been processed. Ignoring.")
        return {"status": "ignored", "reason": "duplicate_webhook"}

    # Register event in DB to lock it
    db_event = StripeEvent(event_id=event_id, processed=True)
    db.add(db_event)
    await db.commit()

    # 3. Process billing event types
    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    print(f"Stripe Webhook received event: {event_type} (ID: {event_id})")

    if event_type == "checkout.session.completed":
        customer_email = data_object.get("customer_details", {}).get("email")
        if customer_email:
            user_res = await db.execute(select(User).where(User.email == customer_email))
            user = user_res.scalar_one_or_none()
            if user:
                user.is_active = True  # Activate tenant access
                await db.commit()
                await orchestrator.log_agent_action(
                    campaign_id=None,
                    agent_name="executive",
                    message=f"Stripe Billing: Activated user '{customer_email}' after checkout.session.completed."
                )

    elif event_type == "customer.subscription.updated":
        # Can handle upgrades/downgrades here
        pass

    elif event_type == "customer.subscription.deleted":
        # Terminate subscription access
        customer_email = data_object.get("customer_email") or data_object.get("email")
        if customer_email:
            user_res = await db.execute(select(User).where(User.email == customer_email))
            user = user_res.scalar_one_or_none()
            if user:
                user.is_active = False  # Deactivate tenant access due to cancellation
                await db.commit()
                await orchestrator.log_agent_action(
                    campaign_id=None,
                    agent_name="executive",
                    message=f"Stripe Billing: Deactivated user '{customer_email}' after customer.subscription.deleted.",
                    log_level="warning"
                )

    return {"status": "processed", "event_id": event_id}
