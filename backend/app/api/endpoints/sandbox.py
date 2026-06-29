from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_operator
from app.database import get_db
from app.models import User
from app.services.sandbox_executor import sandbox_executor
from app.core.orchestrator import orchestrator

router = APIRouter(prefix="/sandbox", tags=["Sandboxed Code Executor"])

class SandboxExecutionRequest(BaseModel):
    code: str

@router.post("/execute")
async def execute_sandboxed_code(
    payload: SandboxExecutionRequest,
    current_user: User = Depends(get_current_operator)
):
    """
    Exposes a JWT-guarded endpoint to compile and run Python code snippets inside
    an isolated subprocess sandbox. Streams stdout/stderr results to client telemetry.
    """
    code_to_run = payload.code

    # Execute inside isolation sandbox
    result = sandbox_executor.execute(code_to_run)

    # Format agent log output telemetry
    log_msg = f"[SANDBOX] Status: {result['status']}. Exit Code: {result['exit_code']}."
    if result["stdout"]:
        log_msg += f"\nSTDOUT:\n{result['stdout']}"
    if result["stderr"]:
        log_msg += f"\nSTDERR:\n{result['stderr']}"

    # Log action to database and broadcast to telemetry websockets
    await orchestrator.log_agent_action(
        campaign_id=None,
        agent_name="sandbox",
        message=log_msg,
        log_level="info" if result["status"] == "success" else "error"
    )

    if result["status"] == "rejected":
        # Return 400 Bad Request if the static AST check blocks dangerous symbols
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Security Violation: Dangerous code signature detected by AST static analyzer.",
                "errors": result["stderr"].split("\n")
            }
        )

    return result


class RegisterModuleRequest(BaseModel):
    name: str
    source_code: str
    config_schema: Dict[str, Any] = {}

class ModuleResponseSchema(BaseModel):
    id: str
    path: str
    config_schema: Dict[str, Any]
    is_active: bool

    class Config:
        from_attributes = True

@router.post("/modules", response_model=ModuleResponseSchema)
async def register_sandbox_module(
    payload: RegisterModuleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Registers or updates a dynamic code module in the database registry."""
    from app.services.module_manager import module_manager
    try:
        module = await module_manager.register_module(
            db=db,
            name=payload.name,
            source_code=payload.source_code,
            config_schema=payload.config_schema
        )
        return module
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/modules", response_model=list[ModuleResponseSchema])
async def list_sandbox_modules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Retrieves all dynamic modules registered in the sandbox system."""
    from app.models import ModuleRegistry
    from sqlalchemy import select
    result = await db.execute(select(ModuleRegistry).order_by(ModuleRegistry.id.asc()))
    return result.scalars().all()

class RunModuleRequest(BaseModel):
    config_params: Dict[str, Any] = {}
    use_wsl: bool = False

@router.post("/modules/{name}/execute")
async def execute_sandbox_module(
    name: str,
    payload: RunModuleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator)
):
    """Executes a registered module's run(params) function in the isolated sandbox."""
    from app.services.module_manager import module_manager
    try:
        res = await module_manager.execute_module(
            db=db,
            name=name,
            config_params=payload.config_params,
            use_wsl=payload.use_wsl
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
