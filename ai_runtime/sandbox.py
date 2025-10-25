"""
Sandbox Runtime - Safe code execution environment with module protection
"""
import os
import subprocess
import sys
import ast
from pathlib import Path
from typing import Dict, Any, Optional
from .memory import RuntimeMemory


class SandboxRuntime:
    """Executes code in a controlled environment with safety checks"""
    
    def __init__(self, project_root: str, memory: RuntimeMemory):
        self.project_root = Path(project_root)
        self.memory = memory
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.history = []
        
        # Safety limits
        self.max_file_size = 50000  # 50KB max per file
        self.max_line_changes = 500  # Max lines changed in one edit

    def _record_action(self, action: str, result: Dict[str, Any], step_id: Optional[int] = None):
        """Record action in history and database"""
        self.history.append({"action": action, "result": result})
        if step_id:
            self.memory.log_action(
                step_id=step_id,
                action_type=action,
                params=result.get('params', {}),
                result=result,
                success=result.get('success', False)
            )

    def _check_path_safety(self, filepath: str) -> Dict[str, Any]:
        """Check if path is safe to modify"""
        full_path = self.project_root / filepath
        
        # Check if path tries to escape project root
        try:
            full_path.resolve().relative_to(self.project_root.resolve())
        except ValueError:
            return {
                "success": False,
                "error": "Path escapes project root"
            }
        
        # Check if module is frozen
        if self.memory.is_path_frozen(filepath):
            return {
                "success": False,
                "error": f"Module containing {filepath} is frozen"
            }
        
        return {"success": True}

    def create_file(self, filepath: str, content: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new file"""
        safety_check = self._check_path_safety(filepath)
        if not safety_check["success"]:
            result = {"success": False, **safety_check}
            self._record_action("create_file", result, step_id)
            return result
        
        full_path = self.project_root / filepath
        
        # Check file size
        if len(content) > self.max_file_size:
            result = {
                "success": False,
                "error": f"File too large ({len(content)} bytes > {self.max_file_size})"
            }
            self._record_action("create_file", result, step_id)
            return result
        
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            result = {
                "success": True,
                "filepath": filepath,
                "message": f"Created {filepath}"
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        self._record_action("create_file", result, step_id)
        return result

    def read_file(self, filepath: str) -> Dict[str, Any]:
        """Read file contents"""
        full_path = self.project_root / filepath
        
        if not full_path.exists():
            return {
                "success": False,
                "error": f"File {filepath} does not exist"
            }
        
        try:
            content = full_path.read_text()
            return {
                "success": True,
                "content": content,
                "filepath": filepath
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def modify_file(self, filepath: str, new_content: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Modify existing file with new content"""
        safety_check = self._check_path_safety(filepath)
        if not safety_check["success"]:
            result = {"success": False, **safety_check}
            self._record_action("modify_file", result, step_id)
            return result
        
        full_path = self.project_root / filepath
        
        if not full_path.exists():
            result = {
                "success": False,
                "error": f"File {filepath} does not exist"
            }
            self._record_action("modify_file", result, step_id)
            return result
        
        # Check size
        if len(new_content) > self.max_file_size:
            result = {
                "success": False,
                "error": f"File too large ({len(new_content)} bytes > {self.max_file_size})"
            }
            self._record_action("modify_file", result, step_id)
            return result
        
        try:
            # Backup old content
            old_content = full_path.read_text()
            
            # Write new content
            full_path.write_text(new_content)
            
            # Syntax gate for Python files
            if filepath.endswith(".py"):
                ok, msg = self._python_syntax_ok(full_path)
                if not ok:
                    full_path.write_text(old_content) # Auto-revert
                    result = {
                        "success": False,
                        "error": f"Syntax check failed: {msg}",
                        "reverted": True
                    }
                    self._record_action("modify_file", result, step_id)
                    return result

            result = {
                "success": True,
                "filepath": filepath,
                "message": f"Modified {filepath}",
                "old_lines": len(old_content.splitlines()),
                "new_lines": len(new_content.splitlines())
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        self._record_action("modify_file", result, step_id)
        return result

    def delete_file(self, filepath: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Delete a file"""
        safety_check = self._check_path_safety(filepath)
        if not safety_check["success"]:
            result = {"success": False, **safety_check}
            self._record_action("delete_file", result, step_id)
            return result
        
        full_path = self.project_root / filepath
        
        try:
            if full_path.exists():
                full_path.unlink()
                result = {
                    "success": True,
                    "message": f"Deleted {filepath}"
                }
            else:
                result = {
                    "success": False,
                    "error": f"File {filepath} does not exist"
                }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        self._record_action("delete_file", result, step_id)
        return result

    def run_python(self, command: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute Python code"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", command],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            response = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            response = {
                "success": False,
                "error": "Command timed out after 30 seconds"
            }
        except Exception as e:
            response = {
                "success": False,
                "error": str(e)
            }
        
        self._record_action("run_python", response, step_id)
        return response

    def _python_syntax_ok(self, path: Path) -> tuple:
        """Checks if a Python file has valid syntax."""
        try:
            with open(path, 'r') as f:
                source = f.read()
            ast.parse(source)
            return True, "ok"
        except SyntaxError as e:
            return False, f"line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)

    def run_shell(self, command: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute shell command"""
        # Command checks
        BLOCKED = ["rm -rf", "sudo", "chmod 777", "wget ", "curl "]
        for bad in BLOCKED:
            if bad in command.lower():
                result = {
                    "success": False,
                    "error": f"Blocked dangerous command fragment '{bad}'",
                    "safety_violation": True
                }
                self._record_action("run_shell", result, step_id)
                return result

        ALLOWED_PREFIXES = ["pip install", "pytest", "python ", "uvicorn ", "npm install"]
        if not any(command.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            result = {
                "success": False,
                "error": f"Command not allowed: '{command}'",
                "allowed_examples": ALLOWED_PREFIXES
            }
            self._record_action("run_shell", result, step_id)
            return result
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            response = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            response = {
                "success": False,
                "error": "Command timed out"
            }
        except Exception as e:
            response = {
                "success": False,
                "error": str(e)
            }
        
        self._record_action("run_shell", response, step_id)
        return response

    def project_tree(self) -> Dict[str, Any]:
        """Get project directory structure"""
        tree = {}
        
        for item in self.project_root.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(self.project_root)
                tree[str(rel_path)] = "file"
            elif item.is_dir() and item != self.project_root:
                rel_path = item.relative_to(self.project_root)
                tree[str(rel_path) + '/'] = "dir"
        
        return {"tree": tree}

    def execute_directive(self, directive: Dict[str, Any], step_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute a single directive from the AI"""
        action = directive.get("action")
        params = directive.get("parameters", {})
        
        if action == "create_file":
            return self.create_file(params.get("filepath"), params.get("content"), step_id)
        elif action == "read_file":
            return self.read_file(params.get("filepath"))
        elif action == "modify_file":
            return self.modify_file(params.get("filepath"), params.get("new_content"), step_id)
        elif action == "delete_file":
            return self.delete_file(params.get("filepath"), step_id)
        elif action == "run_python":
            return self.run_python(params.get("command"), step_id)
        elif action == "run_shell":
            return self.run_shell(params.get("command"), step_id)
        elif action == "project_tree":
            return self.project_tree()
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
