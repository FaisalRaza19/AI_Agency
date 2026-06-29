from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone

from app.api.dependencies import get_current_operator
from app.database import get_db
from app.models import User, Campaign, CampaignWallet, Lead, AgentLog
from app.core.tasks import execute_campaign_pipeline
from fastapi.responses import FileResponse
from app.services.voice_meeting import voice_meeting_service
from app.services.document_generator import document_generator
from app.services.stripe_billing import stripe_billing_service
from app.core.orchestrator import orchestrator

router = APIRouter(prefix="/campaigns", tags=["Campaigns & Outbound Operations"])

# Pydantic Schemas
class CampaignCreate(BaseModel):
    name: str = Field(..., max_length=100)
    objective: str
    budget: float = Field(100.0, ge=1.0)

class WalletSchema(BaseModel):
    budget: float
    cost_spent: float
    is_liquidated: bool

    class Config:
        from_attributes = True

class CampaignResponse(BaseModel):
    id: str
    name: str
    objective: str
    status: str
    created_at: datetime
    updated_at: datetime
    budget: float
    cost_spent: float
    is_liquidated: bool

    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    qualification_score: float
    verification_status: str
    outreach_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class LogResponse(BaseModel):
    id: int
    agent_name: str
    log_level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

class CloserCallResponse(BaseModel):
    transcript: str
    is_agreed: bool
    agreed_price: float
    contract_url: Optional[str] = None
    checkout_url: Optional[str] = None
    summary: str

# Endpoints
@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Creates a new marketing campaign, configures its initial budget wallet,
    and queues it for execution in Celery background workers.
    """
    # 1. Create campaign entry
    db_campaign = Campaign(
        name=payload.name,
        objective=payload.objective,
        status="active"
    )
    db.add(db_campaign)
    await db.flush() # Flush to populate ID

    # 2. Create campaign wallet
    db_wallet = CampaignWallet(
        campaign_id=db_campaign.id,
        budget=payload.budget,
        cost_spent=0.0,
        is_liquidated=False
    )
    db.add(db_wallet)
    await db.commit()
    await db.refresh(db_campaign)

    # 3. Trigger background pipeline via Celery
    try:
        execute_campaign_pipeline.delay(db_campaign.id)
    except Exception as e:
        print(f"[CAMPAIGNS] Warning: Celery task dispatch failed: {e}. Campaign is registered, but pipeline is not active.")

    return CampaignResponse(
        id=db_campaign.id,
        name=db_campaign.name,
        objective=db_campaign.objective,
        status=db_campaign.status,
        created_at=db_campaign.created_at,
        updated_at=db_campaign.updated_at,
        budget=db_wallet.budget,
        cost_spent=db_wallet.cost_spent,
        is_liquidated=db_wallet.is_liquidated
    )

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Lists all active and completed campaigns with their budget and spent ratios."""
    query = select(Campaign).order_by(Campaign.created_at.desc())
    res = await db.execute(query)
    campaigns = res.scalars().all()
    
    output = []
    for c in campaigns:
        # Fetch associated wallet
        wallet_res = await db.execute(select(CampaignWallet).where(CampaignWallet.campaign_id == c.id))
        wallet = wallet_res.scalar_one_or_none()
        
        output.append(CampaignResponse(
            id=c.id,
            name=c.name,
            objective=c.objective,
            status=c.status,
            created_at=c.created_at,
            updated_at=c.updated_at,
            budget=wallet.budget if wallet else 100.0,
            cost_spent=wallet.cost_spent if wallet else 0.0,
            is_liquidated=wallet.is_liquidated if wallet else False
        ))
    return output

@router.get("/{campaign_id}/leads", response_model=List[LeadResponse])
async def get_campaign_leads(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Retrieves all qualified outreach leads generated for a specific campaign."""
    query = select(Lead).where(Lead.campaign_id == campaign_id).order_by(Lead.qualification_score.desc())
    res = await db.execute(query)
    return res.scalars().all()

@router.get("/{campaign_id}/logs", response_model=List[LogResponse])
async def get_campaign_logs(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Retrieves execution logs for a specific campaign."""
    query = select(AgentLog).where(AgentLog.campaign_id == campaign_id).order_by(AgentLog.created_at.desc()).limit(100)
    res = await db.execute(query)
    return res.scalars().all()

@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Pauses execution of a campaign pipeline."""
    query = select(Campaign).where(Campaign.id == campaign_id)
    res = await db.execute(query)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    campaign.status = "paused"
    await db.commit()
    
    wallet_res = await db.execute(select(CampaignWallet).where(CampaignWallet.campaign_id == campaign_id))
    wallet = wallet_res.scalar_one_or_none()
    
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        objective=campaign.objective,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        budget=wallet.budget if wallet else 100.0,
        cost_spent=wallet.cost_spent if wallet else 0.0,
        is_liquidated=wallet.is_liquidated if wallet else False
    )

@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Resumes execution of a paused campaign pipeline."""
    query = select(Campaign).where(Campaign.id == campaign_id)
    res = await db.execute(query)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    campaign.status = "active"
    await db.commit()
    
    wallet_res = await db.execute(select(CampaignWallet).where(CampaignWallet.campaign_id == campaign_id))
    wallet = wallet_res.scalar_one_or_none()
    
    # Re-trigger background task
    try:
        execute_campaign_pipeline.delay(campaign.id)
    except Exception as e:
        print(f"[CAMPAIGNS] Warning: Celery task dispatch failed: {e}")

    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        objective=campaign.objective,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        budget=wallet.budget if wallet else 100.0,
        cost_spent=wallet.cost_spent if wallet else 0.0,
        is_liquidated=wallet.is_liquidated if wallet else False
    )

@router.post("/{campaign_id}/leads/{lead_id}/simulate-closer", response_model=CloserCallResponse)
async def simulate_closer_call(
    campaign_id: str,
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Simulates a closing call transcript for a given lead, analyses negotiation outcomes
    via LLM, compiles contract agreements, and builds Stripe billing links.
    """
    # 1. Verify lead exists and is linked to the campaign
    query = select(Lead).where(Lead.id == lead_id, Lead.campaign_id == campaign_id)
    res = await db.execute(query)
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found in this campaign.")

    # Fetch campaign context
    campaign_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = campaign_res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign context not found.")

    # 2. Run simulation & parse outcomes
    transcript, analysis = await voice_meeting_service.simulate_closer_call(
        lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "Prospect",
        company=lead.company or "Business Entity",
        objective=campaign.objective
    )

    contract_url = None
    checkout_url = None

    if analysis.is_agreed:
        # Update lead state to contract_pending
        lead.outreach_status = "contract_pending"
        await db.commit()

        # Generate signed HTML contract agreement
        await document_generator.generate_contract(
            lead_id=lead.id,
            company=lead.company or "Client Entity",
            agreed_price=analysis.agreed_price
        )
        contract_url = f"/api/v1/campaigns/{campaign_id}/leads/{lead_id}/contract"

        # Generate Stripe checkout page URL passing metadata hooks
        checkout_url = await stripe_billing_service.create_checkout_session(
            lead_id=lead.id,
            campaign_id=campaign_id,
            email=lead.email,
            company=lead.company or "Client Entity",
            amount=analysis.agreed_price
        )

        # Log actions
        await orchestrator.log_agent_action(
            campaign_id=campaign_id,
            agent_name="deal_closer",
            message=f"[CLOSER] Voice discovery call concluded with agreement. Price negotiated: ${analysis.agreed_price:,.2f}/mo. Contract generated, Stripe session created."
        )
    else:
        # Update lead state to declined
        lead.outreach_status = "declined"
        await db.commit()
        
        await orchestrator.log_agent_action(
            campaign_id=campaign_id,
            agent_name="deal_closer",
            message=f"[CLOSER] Discovery call concluded. Prospect declined proposal.",
            log_level="warning"
        )

    return CloserCallResponse(
        transcript=transcript,
        is_agreed=analysis.is_agreed,
        agreed_price=analysis.agreed_price,
        contract_url=contract_url,
        checkout_url=checkout_url,
        summary=analysis.summary
    )

@router.get("/{campaign_id}/leads/{lead_id}/contract")
async def get_lead_contract(
    campaign_id: str,
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Streams the lead's signed HTML contract file securely from disk
    only after confirming active operator rights.
    """
    import os
    # Verify lead exists and belongs to campaign
    query = select(Lead).where(Lead.id == lead_id, Lead.campaign_id == campaign_id)
    res = await db.execute(query)
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found for this campaign")

    # Sanitize filename and retrieve from private storage provider root
    safe_name = os.path.basename(f"{lead_id}_contract.html")
    filepath = os.path.join("storage/contracts", safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Contract agreement has not been generated yet.")

    return FileResponse(filepath, media_type="text/html", filename=f"contract_{lead.company}.html")


class GenerateDeliverableRequest(BaseModel):
    content_type: str  # "email", "blog_post", "ad_copy"
    lead_id: Optional[str] = None

class DeliverableResponse(BaseModel):
    id: str
    campaign_id: str
    lead_id: Optional[str]
    title: str
    content_type: str
    content_body: str
    image_url: Optional[str]
    status: str
    refinement_count: int
    qa_feedback: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/{campaign_id}/deliverables/generate", response_model=DeliverableResponse)
async def generate_campaign_deliverable(
    campaign_id: str,
    payload: GenerateDeliverableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Spawns Content Builder to write marketing assets, then runs QA Validator checks.
    """
    from app.models import Campaign, Lead, Deliverable
    from app.services.content_builder import content_builder_service
    from app.services.qa_validator import qa_validator_service

    # Verify campaign exists
    campaign_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = campaign_res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    company_name = "Target Audience"
    if payload.lead_id:
        lead_res = await db.execute(select(Lead).where(Lead.id == payload.lead_id))
        lead = lead_res.scalar_one_or_none()
        if lead and lead.company:
            company_name = lead.company

    # 1. Generate content
    generated = await content_builder_service.generate_deliverable(
        company=company_name,
        content_type=payload.content_type,
        objective=campaign.objective
    )

    image_url = None
    if payload.content_type in ["ad_copy", "blog_post"]:
        image_url = content_builder_service.generate_dalle_image_url()

    # 2. Save Deliverable in draft status
    deliverable = Deliverable(
        campaign_id=campaign_id,
        lead_id=payload.lead_id,
        title=generated.title,
        content_type=payload.content_type,
        content_body=generated.body,
        image_url=image_url,
        status="draft"
    )
    db.add(deliverable)
    await db.commit()
    await db.refresh(deliverable)

    # 3. Validate deliverable
    validated = await qa_validator_service.validate_and_refine_deliverable(db, deliverable.id)
    return validated

@router.get("/{campaign_id}/deliverables", response_model=List[DeliverableResponse])
async def list_campaign_deliverables(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Lists all generated deliverables/marketing assets for the campaign channel."""
    from app.models import Deliverable
    result = await db.execute(
        select(Deliverable)
        .where(Deliverable.campaign_id == campaign_id)
        .order_by(Deliverable.created_at.desc())
    )
    return result.scalars().all()

class RebuildDeliverableRequest(BaseModel):
    custom_feedback: Optional[str] = None

@router.post("/{campaign_id}/deliverables/{deliverable_id}/rebuild", response_model=DeliverableResponse)
async def rebuild_campaign_deliverable(
    campaign_id: str,
    deliverable_id: str,
    payload: RebuildDeliverableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Manually forces refinement/rebuild of a deliverable using QA feedback or custom prompt notes.
    """
    import json
    from app.models import Deliverable, Campaign
    from app.core.gemini_client import llm_client
    from app.services.qa_validator import qa_validator_service

    # Load deliverable
    result = await db.execute(
        select(Deliverable)
        .where(Deliverable.id == deliverable_id, Deliverable.campaign_id == campaign_id)
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    campaign_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = campaign_res.scalar_one_or_none()
    objective = campaign.objective if campaign else "Outbound marketing outreach"

    # Refinement Prompt
    feedback_context = payload.custom_feedback or deliverable.qa_feedback or "Improve copy structure."
    system_prompt = (
        "You are an expert copywriter refining a draft based on editor feedback.\n"
        "Integrate the feedback context cleanly. Return a JSON object with 'title' and 'body' keys."
    )
    prompt = (
        f"Original Title: {deliverable.title}\n"
        f"Original Body:\n{deliverable.content_body}\n\n"
        f"Strategic Objective: {objective}\n"
        f"Editor Feedback to resolve:\n{feedback_context}\n"
    )

    try:
        res_text = await llm_client.generate_text(prompt, system_prompt, json_mode=True)
        data = json.loads(res_text)
        deliverable.title = data.get("title", deliverable.title)
        deliverable.content_body = data.get("body", deliverable.content_body)
        await db.commit()
    except Exception as e:
        print(f"[CAMPAIGNS] Rebuild generation failed: {e}")

    # Re-run validation checks
    validated = await qa_validator_service.validate_and_refine_deliverable(db, deliverable.id)
    return validated
