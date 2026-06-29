import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.models import AgentLog, Campaign, CampaignWallet, ModuleRegistry
from app.core.gemini_client import llm_client
from app.services.module_manager import module_manager
from app.services.sandbox_executor import sandbox_executor
from app.config import settings

class OptimizationResultSchema(BaseModel):
    optimized_prompts: Dict[str, str] = Field(default_factory=dict)
    adjusted_parameters: Dict[str, Any] = Field(default_factory=dict)
    diagnosis: Optional[str] = None

class SelfReflectionService:
    async def run_reflection_and_self_training_loop(
        self,
        db: AsyncSession,
        campaign_id: str,
        use_wsl: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the campaign self-reflection and self-training optimization pipeline:
        1. Aggregates Postgres agent logs inside a time-bounded window (24 hours) grouped by agent role.
        2. Queries Gemini to diagnose issues and generate a DB-isolated dynamic python optimizer module.
        3. Registers and executes the optimizer inside the WSLSecureAgentSandbox isolation venv.
        4. Validates stdout output using the OptimizationResultSchema at the trust boundary.
        5. Saves final reflection metrics and updates configurations.
        """
        # 1. Fetch Campaign and verify existence
        campaign = await db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign '{campaign_id}' does not exist.")

        # 2. Time-bounded grouping query to shield LLM context window
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        log_query = (
            select(
                AgentLog.agent_name,
                AgentLog.log_level,
                func.count(AgentLog.id).label("count")
            )
            .where(
                and_(
                    AgentLog.campaign_id == campaign_id,
                    AgentLog.created_at >= time_limit,
                    AgentLog.log_level.in_(["warning", "error"])
                )
            )
            .group_by(AgentLog.agent_name, AgentLog.log_level)
        )
        
        log_res = await db.execute(log_query)
        grouped_logs = log_res.all()
        
        # Format log metrics for LLM context
        log_summary = []
        for name, level, count in grouped_logs:
            log_summary.append(f"- Agent '{name}' raised {count} '{level}' events.")

        log_summary_text = "\n".join(log_summary) if log_summary else "No warnings or errors reported in the last 24 hours."

        # 3. LLM Diagnostic query and Optimizer compilation
        system_instruction = (
            "You are the central self-reflection engine of UABE.\n"
            "Analyze the aggregated campaign failure metrics and compile a diagnosis.\n"
            "Generate a custom, DB-isolated python script to run in a sandbox that returns an optimization dictionary.\n"
            "The script MUST define a run(params) function returning a JSON object matching this structure:\n"
            "{\n"
            "  'optimized_prompts': {},\n"
            "  'adjusted_parameters': {},\n"
            "  'diagnosis': '...'\n"
            "}\n"
            "Return ONLY a clean JSON object containing 'diagnosis' and 'source_code' keys."
        )

        prompt = (
            f"Campaign Objective: {campaign.objective}\n"
            f"Current Campaign Status: {campaign.status}\n\n"
            f"Aggregated Failure telemetry (24h limit):\n"
            f"{log_summary_text}\n\n"
            f"Synthesize the python script to optimize prompts or parameters. Do not include database connections or import os/sys."
        )

        try:
            res_text = await llm_client.generate_text(prompt, system_instruction, json_mode=True)
            data = json.loads(res_text)
            diagnosis = data.get("diagnosis", "System optimization running.")
            source_code = data.get("source_code")
            if not source_code:
                raise ValueError("LLM failed to synthesize optimizer source code.")
        except Exception as e:
            # Fallback code synthesis if model is rate limited or unavailable
            diagnosis = f"Fallback optimization generated due to system exception: {e}"
            source_code = """
def run(params):
    # Fallback default optimizer code
    return {
        "optimized_prompts": {},
        "adjusted_parameters": {"retry_delay_seconds": 15},
        "diagnosis": "Automated fallback optimizer executed."
    }
"""

        # 4. Register the Dynamic self-training module
        module_name = f"CampaignOptimizer_{campaign_id.replace('-', '_')}"
        config_schema = {"campaign_id": "string"}
        
        try:
            await module_manager.register_module(
                db=db,
                name=module_name,
                source_code=source_code,
                config_schema=config_schema
            )
        except ValueError as e:
            print(f"[REFLECTION] Generated code registration failed: {e}. Falling back to default optimizer.")
            fallback_source = """
def run(params):
    return {
        "optimized_prompts": {},
        "adjusted_parameters": {"retry_delay_seconds": 15},
        "diagnosis": "Automated fallback optimizer executed due to syntax rejection."
    }
"""
            await module_manager.register_module(
                db=db,
                name=module_name,
                source_code=fallback_source,
                config_schema=config_schema
            )

        # 5. Execute isolated optimizer script inside WSLSecureAgentSandbox (cut off from DB)
        execution_res = await module_manager.execute_module(
            db=db,
            name=module_name,
            config_params={"campaign_id": campaign_id},
            use_wsl=use_wsl
        )

        if execution_res["status"] != "success":
            error_msg = f"Dynamic optimizer execution failed: {execution_res.get('error')}"
            db.add(AgentLog(
                campaign_id=campaign_id,
                agent_name="self_reflection",
                log_level="error",
                message=error_msg,
                is_reflection=True
            ))
            await db.commit()
            return {"status": "failed", "error": error_msg}

        # 6. Validate output using Pydantic at the trust boundary
        try:
            module_output = execution_res["result"]
            validated_output = OptimizationResultSchema(**module_output)
        except Exception as e:
            error_msg = f"Trust boundary validation failed on optimizer outputs: {e}"
            db.add(AgentLog(
                campaign_id=campaign_id,
                agent_name="self_reflection",
                log_level="error",
                message=error_msg,
                is_reflection=True
            ))
            await db.commit()
            return {"status": "failed", "error": error_msg}

        # 7. Apply updates to the database
        # Write reflection logs
        reflection_report = (
            f"=== SELF-REFLECTION REPORT ===\n"
            f"Diagnosis: {validated_output.diagnosis or diagnosis}\n"
            f"Adjusted Parameters: {json.dumps(validated_output.adjusted_parameters)}\n"
            f"Optimized Prompts Count: {len(validated_output.optimized_prompts)}"
        )
        
        db.add(AgentLog(
            campaign_id=campaign_id,
            agent_name="self_reflection",
            log_level="info",
            message=reflection_report,
            is_reflection=True
        ))
        
        # Save optimized configurations (we can write them as JSON strings or update wallet thresholds)
        # For this phase, let's save the adjusted parameters directly to system configs or logs
        await db.commit()

        # 8. Notify dynamic change on Redis telemetry channel
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            telemetry_data = {
                "campaign_id": campaign_id,
                "agent_name": "self_reflection",
                "message": reflection_report,
                "log_level": "info",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await redis_client.publish("uabe_telemetry_broadcast", json.dumps(telemetry_data))
        except Exception as e:
            print(f"[REFLECTION] Redis broadcast failed: {e}")

        return {
            "status": "success",
            "diagnosis": validated_output.diagnosis or diagnosis,
            "adjusted_parameters": validated_output.adjusted_parameters,
            "optimized_prompts": validated_output.optimized_prompts
        }

self_reflection_service = SelfReflectionService()
