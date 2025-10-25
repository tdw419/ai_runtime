import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

class GitManager:
    """Atomic Git operations for safe AI development"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._ensure_git_init()

    def _ensure_git_init(self):
        """Initialize Git repo if not exists"""
        if not (self.project_root / ".git").exists():
            self.run_git("init")
            self.run_git("config user.name 'AI Runtime'")
            self.run_git("config user.email 'ai@runtime.local'")

    def run_git(self, command: str) -> Dict[str, Any]:
        """Execute git command safely"""
        try:
            result = subprocess.run(
                f"git {command}",
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_step_branch(self, step_id: int, description: str) -> Dict[str, Any]:
        """Create isolated branch for a development step"""
        branch_name = f"ai-step-{step_id}"
        result = self.run_git(f"checkout -b {branch_name}")
        if result["success"]:
            self.run_git("add -A")
            self.run_git(f'commit -m "AI Step {step_id}: {description}"')
        return result

    def commit_changes(self, message: str) -> Dict[str, Any]:
        """Commit current changes"""
        self.run_git("add -A")
        return self.run_git(f'commit -m "{message}"')

    def rollback_step(self, step_id: int) -> Dict[str, Any]:
        """Rollback to previous safe state"""
        # Method 1: Reset to main branch
        self.run_git("checkout main")
        self.run_git(f"branch -D ai-step-{step_id}")
        return {"success": True, "action": "rollback_completed"}

    def get_diff(self, filepath: str = "") -> str:
        """Get diff for review"""
        result = self.run_git(f"diff {filepath}")
        return result.get("stdout", "")
