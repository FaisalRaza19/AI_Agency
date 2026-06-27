import asyncio
from typing import Dict, Any
from app.services.celery_app import celery_app
from app.core.orchestrator import orchestrator

def run_async(coro):
    """
    Utility wrapper to run asynchronous coroutines inside Celery synchronous workers.
    Ensures safe loop lifecycle management.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # In case Celery runs in an environment where a loop is already active
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        return loop.run_until_complete(coro)

@celery_app.task(name="tasks.execute_campaign_pipeline")
def execute_campaign_pipeline(campaign_id: str):
    """
    Background job triggered when a campaign starts.
    Autonomously generates milestones and routes execution steps.
    """
    async def pipeline_run():
        await orchestrator.log_agent_action(
            campaign_id=campaign_id,
            agent_name="executive",
            message="Background execution pipeline initiated via Celery worker."
        )
        # Parse objective to actionable steps
        steps = await orchestrator.parse_objective_to_milestones(campaign_id)
        
        # Sequentially execute milestones, checking budget limits at each node
        for step in steps:
            if not await orchestrator.check_budget_gate(campaign_id):
                break
            await orchestrator.route_execution_step(campaign_id, step)
            
    run_async(pipeline_run())
    return f"Pipeline execution completed for campaign {campaign_id}."

@celery_app.task(name="tasks.run_budget_guardrails")
def run_budget_guardrails(campaign_id: str):
    """
    Celery daemon task dedicated to executing budget gate checks independently.
    Can be run as a periodic cron job.
    """
    async def guardrail_run():
        is_safe = await orchestrator.check_budget_gate(campaign_id)
        return is_safe
        
    result = run_async(guardrail_run())
    return f"Campaign budget security check returned: {result}"

@celery_app.task(name="tasks.nightly_agent_reflection")
def nightly_agent_reflection():
    """
    Asynchronous cron reflection task.
    Consolidates logs, compiles lessons learned, and indexes vector memory.
    """
    async def reflection_run():
        print("Starting nightly self-reflection training loop across all logs...")
        # Mock consolidation logic - will hit models inside sandbox in Phase 5
        await asyncio.sleep(1.0)
        print("Self-reflection and vector memory consolidation completed.")
        
    run_async(reflection_run())
    return "Nightly agent reflection compiled successfully."
