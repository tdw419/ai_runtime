# ai_runtime/code_validator.py
import ast
from pathlib import Path
from typing import Dict, Any

class CodeValidator:
    """A class to validate code quality."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_syntax(self, filepath: str) -> Dict[str, Any]:
        """Check the syntax of a Python file."""
        try:
            full_path = self.project_root / filepath
            with open(full_path, 'r') as f:
                source = f.read()
            ast.parse(source)
            return {"success": True}
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"SyntaxError in {filepath} on line {e.lineno}: {e.msg}",
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading {filepath}: {e}"}

    def run_lint(self, filepath: str) -> Dict[str, Any]:
        """Run a linter on a Python file."""
        try:
            from pylint import epylint as lint
            full_path = self.project_root / filepath
            stdout, stderr = lint.py_run(str(full_path), return_std=True)
            output = stdout.getvalue()
            errors = stderr.getvalue()

            # Pylint exits with a non-zero status code for warnings, so we check for "rated"
            success = "rated" in output or not errors

            return {
                "success": success,
                "output": output,
                "errors": errors
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_tests(self, test_path: str) -> Dict[str, Any]:
        """Run unit tests."""
        try:
            import pytest
            full_path = self.project_root / test_path
            result = pytest.main([str(full_path)])

            return {
                "success": result == pytest.ExitCode.OK,
                "exit_code": result.value
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
