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
    Checks code strings statically, compiles, and runs them inside isolated subprocess frames.
    """
    def __init__(self, timeout_limit: float = 5.0):
        self.timeout_limit = timeout_limit

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

    def execute(self, code_str: str) -> Dict[str, Any]:
        """
        Validates and executes a code snippet.
        Enforces a execution timeout, captures stdout/stderr, and terminates zombie processes.
        """
        # 1. Run static checks first
        violations = self.static_analyze(code_str)
        if violations:
            return {
                "status": "rejected",
                "stdout": "",
                "stderr": "\n".join(violations),
                "exit_code": -1
            }

        # 2. Write code to a temporary script file
        fd, temp_file_path = tempfile.mkstemp(suffix=".py", text=True)
        try:
            with os.fdopen(fd, "w") as tmp:
                tmp.write(code_str)

            # 3. Launch isolated subprocess execution
            process = subprocess.Popen(
                [sys.executable, temp_file_path],
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
                # 4. Clean zombie process termination on timeout (explicit task kill / termination)
                process.kill()
                # Await child to ensure it's fully cleaned up from system resources
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
