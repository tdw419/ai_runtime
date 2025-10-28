import ast
from pathlib import Path

class CodeGuard:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()

    def is_path_safe(self, filepath: str) -> bool:
        """Ensure the filepath is within the workspace directory."""
        full_path = (self.workspace_root / filepath).resolve()
        return str(full_path).startswith(str(self.workspace_root))

    def validate_python_syntax(self, code: str) -> bool:
        """Check if the code is valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def apply_edit(self, filepath: str, new_contents: str) -> dict:
        """Apply a file edit if the path is safe and the code is valid."""
        if not self.is_path_safe(filepath):
            return {"success": False, "error": f"Unsafe path: {filepath}"}

        if filepath.endswith(".py") and not self.validate_python_syntax(new_contents):
            return {"success": False, "error": f"Invalid Python syntax in {filepath}"}

        full_path = self.workspace_root / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(new_contents)
        return {"success": True, "filepath": str(full_path)}
