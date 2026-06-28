from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.api.dependencies import get_current_operator
from app.database import get_db
from app.models import User, SystemConfig, StagedPrompt
from app.config import set_config_value, get_config_value, config_resolver

router = APIRouter(prefix="/settings", tags=["System Settings & Dynamic Configurations"])

# Pydantic Schemas
class SystemConfigSchema(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class StagedPromptSchema(BaseModel):
    id: int
    prompt_key: str
    prompt_text: str
    version: int
    status: str
    benchmark_score: Optional[float] = None

class PromotePromptRequest(BaseModel):
    prompt_id: int

@router.get("", response_model=List[SystemConfigSchema])
async def list_configurations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Lists all encrypted configuration records, decrypting values at the boundary."""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    output = []
    for c in configs:
        decrypted = config_resolver.decrypt(c.value)
        output.append(SystemConfigSchema(
            key=c.key,
            value=decrypted,
            description=c.description
        ))
    return output

@router.post("", response_model=SystemConfigSchema)
async def update_configuration(
    payload: SystemConfigSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Updates/Creates a configuration key-value pair, encrypting value at boundary."""
    await set_config_value(payload.key, payload.value, payload.description)
    return payload

@router.get("/prompts", response_model=List[StagedPromptSchema])
async def list_staged_prompts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Lists all prompts in the staging registry."""
    result = await db.execute(select(StagedPrompt).order_by(StagedPrompt.version.desc()))
    return result.scalars().all()

@router.post("/promote-prompt", status_code=status.HTTP_200_OK)
async def promote_prompt(
    payload: PromotePromptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Promotes/pins a staging prompt to active status, archiving other versions of the same key."""
    # Find target prompt
    prompt_res = await db.execute(select(StagedPrompt).where(StagedPrompt.id == payload.prompt_id))
    target = prompt_res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Prompt record not found.")

    # Mark other versions of the same prompt_key as archived/staged
    await db.execute(
        select(StagedPrompt)
        .where(StagedPrompt.prompt_key == target.prompt_key, StagedPrompt.id != target.id)
    )
    # Perform update
    from sqlalchemy import update
    await db.execute(
        update(StagedPrompt)
        .where(StagedPrompt.prompt_key == target.prompt_key, StagedPrompt.id != target.id)
        .values(status="archived")
    )
    
    target.status = "pinned"
    await db.commit()
    return {"status": "promoted", "prompt_key": target.prompt_key, "version": target.version}


class SenderDomainSchema(BaseModel):
    id: int
    domain: str
    from_email: str
    weight: int
    is_active: bool

@router.get("/domains", response_model=List[SenderDomainSchema])
async def list_sender_domains(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Lists all active outbound sender domains."""
    from app.models import SenderDomain
    result = await db.execute(select(SenderDomain))
    return result.scalars().all()
