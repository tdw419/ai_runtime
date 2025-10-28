# code_guard.py
import ast
from pathlib import Path
from typing import Dict, Any

class CodeGuard:
    def __init__(self, sandbox_root: str):
        self.sandbox_root = Path(sandbox_root).resolve()

    def _resolve_path(self, rel_path: str) -> Path:
        full = (self.sandbox_root / rel_path).resolve()
        if not str(full).startswith(str(self.sandbox_root)):
            raise ValueError(f"Unsafe path outside sandbox: {rel_path}")
        return full

    def is_valid_python(self, text: str) -> bool:
        try:
            ast.parse(text)
            return True
        except SyntaxError:
            return False

    def safe_write_python(self, rel_path: str, text: str) -> Dict[str, Any]:
        try:
            if rel_path.endswith(".py") and not self.is_valid_python(text):
                return {"success": False, "error": "INVALID_SYNTAX"}
            full = self._resolve_path(rel_path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(text)
            return {"success": True, "filepath": str(full), "bytes": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}
