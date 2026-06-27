from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from app.api.dependencies import get_current_operator
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
