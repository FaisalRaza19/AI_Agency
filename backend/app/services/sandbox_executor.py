import ast
import sys
import os
import subprocess
import tempfile
from typing import Dict, Any, List

class SandboxSafetyChecker(ast.NodeVisitor):
    """
    AST-based static code analyzer to intercept code execution frames.
    Checks and rejects malicious/banned builtins, unsafe double-underscore attributes,
    and hidden/nested import statements.
    """
    def __init__(self):
        self.is_safe = True
        self.errors = []
        
        # Banned builtins & functions
        self.banned_names = {
            'exec', 'eval', '__import__', 'open', 'compile', 
            '__builtins__', 'getattr', 'setattr', 'delattr', 'hasattr', 'locals', 'globals'
        }
        
        # Banned package modules
        self.banned_modules = {
            'os', 'sys', 'subprocess', 'shutil', 'builtins', 'socket', 
            'requests', 'pickle', 'importlib', 'ctypes', 'platform', 'threading', 'multiprocessing'
        }

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            base_module = name.name.split('.')[0]
            if base_module in self.banned_modules:
                self.is_safe = False
                self.errors.append(f"Security Alert: Import of banned module '{name.name}' is blocked.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in self.banned_modules:
                self.is_safe = False
                self.errors.append(f"Security Alert: Import from banned module '{node.module}' is blocked.")
        for name in node.names:
            if name.name in self.banned_names or name.name in self.banned_modules:
                self.is_safe = False
                self.errors.append(f"Security Alert: Import of banned symbol '{name.name}' is blocked.")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in self.banned_names:
            self.is_safe = False
            self.errors.append(f"Security Alert: Use of banned builtin/symbol '{node.id}' is blocked.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Prevent accessing double-underscore internal namespaces
        if node.attr in self.banned_names or node.attr.startswith('__'):
            self.is_safe = False
            self.errors.append(f"Security Alert: Accessing private attribute '{node.attr}' is blocked.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Intercept calls that could invoke hidden imports or evaluations
        if isinstance(node.func, ast.Name):
            if node.func.id in self.banned_names:
                self.is_safe = False
                self.errors.append(f"Security Alert: Calling banned function '{node.func.id}' is blocked.")
        self.generic_visit(node)


class SandboxedCodeExecutor:
    """
    Subprocess-isolated sandbox runner.
    Checks code strings statically, compiles, and runs them inside isolated subprocess frames
    using the WSLSecureAgentSandbox virtual environment.
    """
    def __init__(self, timeout_limit: float = 5.0):
        self.timeout_limit = timeout_limit
        self._module_cache = {}

    def clear_module_cache(self):
        """Clears local execution cache for dynamic hot-reloading."""
        self._module_cache.clear()

    def _ensure_sandbox_venv(self) -> tuple[str, str]:
        """Ensures that the isolation virtual environment exists on disk."""
        backend_dir = r"e:\Documents\AI_AGENCY\backend"
        sandbox_dir = os.path.join(backend_dir, "WSLSecureAgentSandbox")
        venv_dir = os.path.join(sandbox_dir, "venv")
        
        if not os.path.exists(venv_dir):
            os.makedirs(sandbox_dir, exist_ok=True)
            # Create venv utilizing the host's base interpreter
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            
        # Select python path
        if os.name == "nt":
            windows_python = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            windows_python = os.path.join(venv_dir, "bin", "python")

        # Convert backslashes for WSL execution
        # e.g., e:\Documents\AI_AGENCY\backend\WSLSecureAgentSandbox\venv\bin\python
        wsl_python = "/mnt/e/Documents/AI_AGENCY/backend/WSLSecureAgentSandbox/venv/bin/python"
        
        return windows_python, wsl_python

    def static_analyze(self, code_str: str) -> List[str]:
        """
        Runs static analysis on the source code string.
        Returns a list of safety violation strings, if any.
        """
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return [f"Syntax Error during compilation: {e.msg} at line {e.lineno}"]

        checker = SandboxSafetyChecker()
        checker.visit(tree)
        return checker.errors

    def execute(self, code_str: str, use_wsl: bool = False, bypass_safety_check: bool = False) -> Dict[str, Any]:
        """
        Validates and executes a code snippet.
        Enforces a execution timeout, captures stdout/stderr, and terminates zombie processes.
        Runs inside the WSLSecureAgentSandbox virtual environment.
        """
        # 1. Run static checks first if not bypassed
        if not bypass_safety_check:
            violations = self.static_analyze(code_str)
            if violations:
                return {
                    "status": "rejected",
                    "stdout": "",
                    "stderr": "\n".join(violations),
                    "exit_code": -1
                }

        # Ensure sandbox virtual environment exists
        windows_python, wsl_python = self._ensure_sandbox_venv()

        # Create temporary storage path inside project root (accessible to WSL)
        backend_dir = r"e:\Documents\AI_AGENCY\backend"
        temp_dir = os.path.join(backend_dir, "storage", "sandbox_temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Write code to temporary file
        fd, temp_file_path = tempfile.mkstemp(dir=temp_dir, suffix=".py", text=True)
        try:
            with os.fdopen(fd, "w") as tmp:
                tmp.write(code_str)

            # Determine command execution array
            if use_wsl:
                # Translate path, e.g., e:\Documents\AI_AGENCY\backend\storage\sandbox_temp\abc.py -> /mnt/e/Documents/AI_AGENCY/backend/storage/sandbox_temp/abc.py
                wsl_script_path = temp_file_path.replace("\\", "/").replace("E:", "/mnt/e").replace("e:", "/mnt/e")
                cmd = ["wsl", wsl_python, wsl_script_path]
            else:
                cmd = [windows_python, temp_file_path]

            # 3. Launch isolated subprocess execution
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            try:
                stdout, stderr = process.communicate(timeout=self.timeout_limit)
                return {
                    "status": "success",
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": process.returncode
                }
            except subprocess.TimeoutExpired:
                # 4. Clean zombie process termination on timeout
                process.kill()
                stdout, stderr = process.communicate()
                
                timeout_msg = f"Security Error: Code execution exceeded the {self.timeout_limit} second timeout limit. Subprocess terminated."
                full_stderr = (stderr + "\n" + timeout_msg) if stderr else timeout_msg
                
                return {
                    "status": "timeout",
                    "stdout": stdout,
                    "stderr": full_stderr,
                    "exit_code": -1
                }
        finally:
            # Cleanup temporary file
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

# Instantiate global sandbox executor client
sandbox_executor = SandboxedCodeExecutor()
