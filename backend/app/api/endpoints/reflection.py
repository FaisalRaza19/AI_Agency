from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.api.dependencies import get_current_operator
from app.database import get_db
from app.models import User, AgentLog
from app.services.self_reflection import self_reflection_service

router = APIRouter(prefix="/campaigns", tags=["Self-Reflection Control Plane"])

class ReflectionResponse(BaseModel):
    status: str
    diagnosis: str
    adjusted_parameters: Dict[str, Any]
    optimized_prompts: Dict[str, str]

class AgentLogResponse(BaseModel):
    id: int
    campaign_id: Optional[str]
    agent_name: str
    log_level: str
    message: str
    is_reflection: bool
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/{campaign_id}/reflect", response_model=ReflectionResponse)
async def trigger_campaign_self_reflection(
    campaign_id: str,
    use_wsl: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Manually triggers the campaign self-reflection and dynamic sandbox optimization loop.
    """
    try:
        res = await self_reflection_service.run_reflection_and_self_training_loop(
            db=db,
            campaign_id=campaign_id,
            use_wsl=use_wsl
        )
        if res.get("status") == "failed":
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{campaign_id}/reflection-logs", response_model=list[AgentLogResponse])
async def list_campaign_reflection_reports(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """
    Lists all self-reflection diagnostic reports and logs recorded for the campaign.
    """
    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.campaign_id == campaign_id, AgentLog.is_reflection == True)
        .order_by(AgentLog.created_at.desc())
    )
    return result.scalars().all()
