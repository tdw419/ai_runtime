# sandbox.py
import subprocess
from pathlib import Path
from typing import Dict, Any

class Sandbox:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, rel_path: str) -> Path:
        full = (self.root / rel_path).resolve()
        if not str(full).startswith(str(self.root)):
            raise ValueError(f"Unsafe path: {rel_path}")
        return full

    def list_tree(self) -> Dict[str, Any]:
        files = [str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file()]
        return {"success": True, "files": sorted(files)}

    def read_file(self, rel_path: str) -> Dict[str, Any]:
        try:
            full = self._safe(rel_path)
            return {"success": True, "filepath": str(full), "content": full.read_text()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, rel_path: str, content: str) -> Dict[str, Any]:
        try:
            full = self._safe(rel_path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
            return {"success": True, "filepath": str(full), "bytes": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_python_file(self, rel_path: str) -> Dict[str, Any]:
        try:
            full = self._safe(rel_path)
            proc = subprocess.run(
                ["python3", str(full)],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
