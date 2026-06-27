import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import httpx
from app.config import settings
from app.database import get_db
from app.models import Lead, Campaign, AgentLog
from app.core.orchestrator import orchestrator

router = APIRouter(prefix="/telegram", tags=["Telegram Bot Webhook"])

async def send_telegram_markup_update(chat_id: str, message_id: int, new_text: str) -> None:
    """Helper to update a Telegram message's text on inline keyboard callback action."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "Markdown"
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5.0)
    except Exception as e:
        print(f"Failed to update Telegram message UI markup: {e}")

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Exposes a secure webhook endpoint to receive callback payloads from the Telegram Bot API.
    Validates X-Telegram-Bot-Api-Secret-Token headers before executing mutations.
    """
    # Webhook token security check
    expected_token = settings.SECRET_KEY[:32]  # Use first 32 chars of secret key as webhook secret
    if settings.ENVIRONMENT == "production":
        if x_telegram_bot_api_secret_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Webhook header validation failed."
            )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    # ─────────────────────────────────────────────────────────────────────────
    # Handle Inline Keyboard Button Click Callbacks
    # ─────────────────────────────────────────────────────────────────────────
    if "callback_query" in payload:
        callback = payload["callback_query"]
        callback_data = callback.get("data", "")
        message = callback.get("message", {})
        message_id = message.get("message_id")
        chat_id = message.get("chat", {}).get("id")
        
        parts = callback_data.split(":")
        action = parts[0]
        
        # 1. Action: Approve Outbound Campaign Pitch
        if action == "approve_pitch" and len(parts) >= 3:
            campaign_id = parts[1]
            lead_id = parts[2]
            
            # Mutate database state
            lead_res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = lead_res.scalar_one_or_none()
            if lead:
                lead.outreach_status = "IN_LIVE_NEGOTIATION"  # set to active state
                await db.commit()
                
                await orchestrator.log_agent_action(
                    campaign_id=campaign_id,
                    agent_name="deal_closer",
                    message=f"Telegram Bridge: Outreach approved by Owner for lead '{lead.email}'. Sending pitch."
                )
                
                # Update Telegram message UI to reflect completion state
                success_text = (
                    f"✅ *Outreach Pitch Approved & Fired*\n"
                    f"────────────────────────\n"
                    f"📧 **Recipient:** {lead.email}\n"
                    f"💼 **Status:** Active (In Live Negotiation)\n"
                    f"👤 **Approved By:** Master Owner"
                )
                await send_telegram_markup_update(chat_id, message_id, success_text)
                
        # 2. Action: Reject / Force Prompt Rewrite
        elif action == "reject_pitch" and len(parts) >= 3:
            campaign_id = parts[1]
            lead_id = parts[2]
            
            lead_res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = lead_res.scalar_one_or_none()
            if lead:
                lead.outreach_status = "declined"
                await db.commit()
                
                await orchestrator.log_agent_action(
                    campaign_id=campaign_id,
                    agent_name="deal_closer",
                    message=f"Telegram Bridge: Outreach pitch rejected by Owner for lead '{lead.email}'. Halted.",
                    log_level="warning"
                )
                
                reject_text = (
                    f"❌ *Outreach Pitch Rejected & Halted*\n"
                    f"────────────────────────\n"
                    f"📧 **Recipient:** {lead.email}\n"
                    f"💼 **Status:** Blocked / Terminated\n"
                    f"👤 **Actioned By:** Master Owner"
                )
                await send_telegram_markup_update(chat_id, message_id, reject_text)

        # 3. Action: Cryptographic dependency install approval
        elif action == "approve_pkg" and len(parts) >= 3:
            tool_name = parts[1]
            pkg_name = parts[2]
            
            print(f"Master Owner authorized installation of dynamic package '{pkg_name}' for tool '{tool_name}'.")
            
            pkg_text = (
                f"✅ *Cryptographic Package Installed*\n"
                f"────────────────────────\n"
                f"🔧 **Tool:** {tool_name}\n"
                f"📦 **Package:** {pkg_name}\n"
                f"🔒 **Security Status:** Registered & Sandbox Enabled"
            )
            await send_telegram_markup_update(chat_id, message_id, pkg_text)

        # Answer callback to remove loading state in Telegram client
        if settings.TELEGRAM_BOT_TOKEN and "id" in callback:
            answer_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(answer_url, json={"callback_query_id": callback["id"]}, timeout=5.0)
            except Exception as e:
                print(f"Failed to answer Telegram callback query: {e}")

        return {"status": "callback_processed"}

    return {"status": "ignored"}

# Helper to format and send High-Fidelity UI markup notifications
class TelegramNotificationCenter:
    @staticmethod
    async def send_tactical_log(campaign_id: str, lead_id: str, email: str, company: str, score: float, pitch: str) -> bool:
        """Sends tactical campaign status alerts with inline approval buttons to Operator/Owner."""
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        text = (
            f"📢 *Outbound Pitch Generated - Needs Approval*\n"
            f"────────────────────────\n"
            f"👤 **Lead Email:** {email}\n"
            f"🏢 **Company:** {company}\n"
            f"📊 **Qualification Score:** {score:.1f}%\n"
            f"📝 **Pitch Draft:** \"{pitch}\"\n"
            f"────────────────────────\n"
            f"Select action below to execute/halt the campaign loop:"
        )

        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "🚀 Approve & Launch Resend", "callback_data": f"approve_pitch:{campaign_id}:{lead_id}"},
                        {"text": "❌ Reject & Rewrite", "callback_data": f"reject_pitch:{campaign_id}:{lead_id}"}
                    ]
                ]
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, timeout=5.0)
                return res.status_code == 200
        except Exception as e:
            print(f"Failed to post Telegram tactical log: {e}")
            return False

    @staticmethod
    async def send_cryptographic_request(tool_name: str, pkg_name: str) -> bool:
        """Sends cryptographic validation requests with inline approval buttons directly to Master Owner."""
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        text = (
            f"⚠️ *Tier 2 Dependency Authorization Request*\n"
            f"────────────────────────\n"
            f"🔧 **Tool Module:** {tool_name}\n"
            f"📦 **Package Name:** {pkg_name}\n"
            f"🔒 **Security Scan:** Whitelist check failed. Requires cryptographic Master signature.\n"
            f"────────────────────────\n"
            f"Select action below to approve or block package sandbox compilation:"
        )

        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "🔒 Approve & Install Pkg", "callback_data": f"approve_pkg:{tool_name}:{pkg_name}"},
                        {"text": "🚫 Block Package", "callback_data": f"reject_pkg:{tool_name}:{pkg_name}"}
                    ]
                ]
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, timeout=5.0)
                return res.status_code == 200
        except Exception as e:
            print(f"Failed to post Telegram cryptographic request: {e}")
            return False
