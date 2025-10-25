"""
Sandbox Runtime - Safe code execution environment with module protection
"""
import os
import subprocess
import sys
import ast
import difflib
from pathlib import Path
from typing import Dict, Any, Optional
from .memory import RuntimeMemory
from . import ast_utils


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

        # Build Docker image once on startup
        print("Building sandbox Docker image...")
        build_result = self._build_docker_image()
        if not build_result["success"]:
            print(f"FATAL: Docker image build failed: {build_result.get('stderr')}")
            # In a real application, this should raise a critical exception.

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
        
        # Diff size cap
        old_content_for_diff = ""
        if full_path.exists():
            try:
                old_content_for_diff = full_path.read_text()
            except Exception:
                pass # Ignore if read fails, proceed with write

        line_diff = abs(len(old_content_for_diff.splitlines()) - len(new_content.splitlines()))
        if line_diff > self.max_line_changes:
             result = {
                "success": False,
                "error": f"Change too large: {line_diff} lines changed (limit {self.max_line_changes})",
                "policy": "diff_cap"
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

    def add_import_ast(self, filepath: str, module_name: str, alias: Optional[str] = None, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Adds an import to a Python file using AST."""
        safety_check = self._check_path_safety(filepath)
        if not safety_check["success"]:
            result = {"success": False, **safety_check}
            self._record_action("add_import_ast", result, step_id)
            return result

        full_path = self.project_root / filepath
        if not full_path.exists():
            result = {"success": False, "error": f"File {filepath} does not exist"}
            self._record_action("add_import_ast", result, step_id)
            return result

        try:
            source_code = full_path.read_text()
            new_code = ast_utils.add_import(source_code, module_name, alias)
            full_path.write_text(new_code)
            result = {
                "success": True,
                "filepath": filepath,
                "message": f"Added import '{module_name}' to {filepath}"
            }
        except Exception as e:
            result = {"success": False, "error": f"AST modification failed: {e}"}

        self._record_action("add_import_ast", result, step_id)
        return result

    def add_function_ast(self, filepath: str, function_code: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Adds or replaces a function in a Python file using AST."""
        safety_check = self._check_path_safety(filepath)
        if not safety_check["success"]:
            result = {"success": False, **safety_check}
            self._record_action("add_function_ast", result, step_id)
            return result

        full_path = self.project_root / filepath
        if not full_path.exists():
            result = {"success": False, "error": f"File {filepath} does not exist"}
            self._record_action("add_function_ast", result, step_id)
            return result

        try:
            # Parse the new function code to get its AST node
            function_tree = ast.parse(function_code)
            new_function_def = None
            for node in function_tree.body:
                if isinstance(node, ast.FunctionDef):
                    new_function_def = node
                    break

            if not new_function_def:
                raise ValueError("The provided code does not contain a valid function definition.")

            source_code = full_path.read_text()
            new_code = ast_utils.add_function(source_code, new_function_def)
            full_path.write_text(new_code)

            result = {
                "success": True,
                "filepath": filepath,
                "message": f"Added/replaced function '{new_function_def.name}' in {filepath}"
            }
        except Exception as e:
            result = {"success": False, "error": f"AST modification failed: {e}"}

        self._record_action("add_function_ast", result, step_id)
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
        """Execute Python code in a Docker container."""
        return self._run_in_docker(f'python -c "{command}"', step_id)

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

    def _generate_diff(self, filepath: str, old_content: str, new_content: str) -> Dict[str, Any]:
        """Generate a unified diff of the changes."""
        diff = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=filepath,
            tofile=filepath,
        ))
        return {
            "diff": "".join(diff),
            "lines_changed": sum(1 for line in diff if line.startswith(('+', '-')) and not line.startswith(('+++', '---')))
        }

    def run_shell(self, command: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute shell command in a Docker container."""
        return self._run_in_docker(command, step_id)

    def _build_docker_image(self):
        """Build the Docker image for the sandbox."""
        try:
            # NOTE: Using 'sudo' as a workaround for environments where the user
            # is not in the 'docker' group. This is a security trade-off for usability
            # in this specific execution context.
            subprocess.run(
                ["sudo", "docker", "build", "-t", "ai-runtime-sandbox", "."],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            return {"success": True}
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": "Docker image build failed",
                "stdout": e.stdout.decode(),
                "stderr": e.stderr.decode(),
            }

    def _run_in_docker(self, command: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Helper to run a command in the Docker sandbox."""
        try:
            # NOTE: See comment in _build_docker_image regarding 'sudo'.
            result = subprocess.run(
                ["sudo", "docker", "run", "--rm", "ai-runtime-sandbox", "sh", "-c", command],
                capture_output=True,
                text=True,
                timeout=60
            )
            response = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            response = {"success": False, "error": "Command timed out"}
        except Exception as e:
            response = {"success": False, "error": str(e)}

        action = "run_python" if command.startswith("python") else "run_shell"
        self._record_action(action, response, step_id)
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
        elif action == "add_import_ast":
            return self.add_import_ast(params.get("filepath"), params.get("module_name"), params.get("alias"), step_id)
        elif action == "add_function_ast":
            return self.add_function_ast(params.get("filepath"), params.get("function_code"), step_id)
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

    def git_commit_step(self, step_title: str) -> Dict[str, Any]:
        """Commit the current state of the project."""
        try:
            subprocess.run(["git", "add", "."], cwd=self.project_root, capture_output=True)
            commit_message = f"AI Step: {step_title}"
            subprocess.run(["git", "commit", "-m", commit_message], cwd=self.project_root, capture_output=True)
            return {"success": True, "message": f"Committed changes for step: {step_title}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
