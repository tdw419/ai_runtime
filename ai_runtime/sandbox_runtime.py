import subprocess
from pathlib import Path
from typing import Dict, Any

class RuntimeSandbox:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def safe_path(self, rel_path: str) -> Path:
        full = (self.workspace_root / rel_path).resolve()
        if not str(full).startswith(str(self.workspace_root)):
            raise ValueError(f"Unsafe path: {rel_path}")
        return full

    def read_file(self, rel_path: str) -> Dict[str, Any]:
        try:
            full = self.safe_path(rel_path)
            text = full.read_text()
            return {"success": True, "filepath": str(full), "content": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, rel_path: str, content: str) -> Dict[str, Any]:
        try:
            full = self.safe_path(rel_path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
            return {"success": True, "filepath": str(full)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def project_tree(self) -> Dict[str, Any]:
        tree = []
        for path in self.workspace_root.rglob("*"):
            if path.is_file():
                tree.append(str(path.relative_to(self.workspace_root)))
        return {"success": True, "files": tree}

    def run_python(self, code: str) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                ["python3", "-c", code],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_python_file(self, rel_path: str) -> Dict[str, Any]:
        try:
            full = self.safe_path(rel_path)
            proc = subprocess.run(
                ["python3", str(full)],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
