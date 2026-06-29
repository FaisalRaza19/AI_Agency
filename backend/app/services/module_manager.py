import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.models import ModuleRegistry
from app.services.sandbox_executor import sandbox_executor
from app.config import settings

class ModuleManagerService:
    def _get_module_disk_path(self, name: str) -> tuple[str, str]:
        """Returns the module file path on Windows disk and its WSL path counterpart."""
        backend_dir = r"e:\Documents\AI_AGENCY\backend"
        modules_dir = os.path.join(backend_dir, "storage", "modules")
        os.makedirs(modules_dir, exist_ok=True)
        
        win_path = os.path.join(modules_dir, f"{name}.py")
        wsl_path = f"/mnt/e/Documents/AI_AGENCY/backend/storage/modules/{name}.py"
        return win_path, wsl_path

    async def register_module(
        self,
        db: AsyncSession,
        name: str,
        source_code: str,
        config_schema: Dict[str, Any]
    ) -> ModuleRegistry:
        """
        Validates safety, registers module in DB, writes source code to disk,
        and broadcasts cache refresh hook to Redis channel.
        """
        # 1. Run static checks
        violations = sandbox_executor.static_analyze(source_code)
        if violations:
            raise ValueError(f"Security Rejection: {', '.join(violations)}")

        # 2. Disk setup
        win_path, wsl_path = self._get_module_disk_path(name)
        with open(win_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        # 3. DB Save/Update
        result = await db.execute(select(ModuleRegistry).where(ModuleRegistry.id == name))
        db_module = result.scalar_one_or_none()
        
        if not db_module:
            db_module = ModuleRegistry(
                id=name,
                path=win_path,
                source_code=source_code,
                config_schema=config_schema,
                is_active=True
            )
            db.add(db_module)
        else:
            db_module.source_code = source_code
            db_module.config_schema = config_schema
            db_module.path = win_path
            
        await db.commit()
        await db.refresh(db_module)

        # 4. Publish refresh signal to Redis
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            payload = {"action": "refresh", "module_name": name}
            await redis_client.publish("uabe:registry:refresh", json.dumps(payload))
            print(f"[MODULE] Published hot-reload token for module '{name}'")
        except Exception as e:
            print(f"[MODULE] Redis publish failed ({e}). Hot-reload reload notification skipped.")

        return db_module

    async def execute_module(
        self,
        db: AsyncSession,
        name: str,
        config_params: Dict[str, Any],
        use_wsl: bool = False
    ) -> Dict[str, Any]:
        """
        Loads registered module, guarantees disk presence, and executes the module's run(params)
        method in the isolated virtual environment sandbox.
        """
        result = await db.execute(select(ModuleRegistry).where(ModuleRegistry.id == name))
        db_module = result.scalar_one_or_none()
        if not db_module:
            raise ValueError(f"Module '{name}' is not registered.")
        if not db_module.is_active:
            raise ValueError(f"Module '{name}' is disabled.")

        # Ensure file exists on disk
        win_path, wsl_path = self._get_module_disk_path(name)
        if not os.path.exists(win_path):
            with open(win_path, "w", encoding="utf-8") as f:
                f.write(db_module.source_code)

        # Build runner wrapper script
        # Imports the target module, loads parameters json, executes run(params), and prints json output
        wsl_import_dir = "/mnt/e/Documents/AI_AGENCY/backend/storage/modules"
        win_import_dir = os.path.dirname(win_path)
        import_dir = wsl_import_dir if use_wsl else win_import_dir

        runner_script = f"""
import sys
import json
sys.path.insert(0, {repr(import_dir)})
try:
    import {name}
    params = json.loads({repr(json.dumps(config_params))})
    res = {name}.run(params)
    print("SUCCESS_OUTPUT:" + json.dumps(res))
except Exception as e:
    import traceback
    print("ERROR_OUTPUT:" + str(e) + "\\n" + traceback.format_exc(), file=sys.stderr)
    sys.exit(1)
"""

        # Run generated wrapper inside sandbox
        res = sandbox_executor.execute(runner_script, use_wsl=use_wsl, bypass_safety_check=True)

        # Parse success or error outputs from captured streams
        if res["exit_code"] == 0 and "SUCCESS_OUTPUT:" in res["stdout"]:
            parts = res["stdout"].split("SUCCESS_OUTPUT:", 1)
            try:
                module_res = json.loads(parts[1].strip())
                return {"status": "success", "result": module_res}
            except Exception as e:
                return {"status": "failed", "error": f"JSON parsing failed on module output: {e}", "stdout": res["stdout"]}
        else:
            err_msg = res["stderr"] or "Module returned non-zero exit code."
            if "ERROR_OUTPUT:" in res["stderr"]:
                err_msg = res["stderr"].split("ERROR_OUTPUT:", 1)[1].strip()
            return {
                "status": "failed",
                "error": err_msg,
                "exit_code": res["exit_code"],
                "stdout": res["stdout"]
            }

module_manager = ModuleManagerService()
