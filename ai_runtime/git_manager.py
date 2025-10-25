import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class GitManager:
    """Atomic Git operations for safe AI development with transactional steps"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.main_branch = "main"
        self._ensure_git_init()

    def _ensure_git_init(self):
        """Initialize Git repo if not exists"""
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            print("🔄 Initializing Git repository...")
            self.run_git("init")
            self.run_git("config user.name 'AI Runtime'")
            self.run_git("config user.email 'ai@runtime.local'")

            # Create initial commit if no commits exist
            result = self.run_git("log --oneline")
            if not result["stdout"].strip():
                # Create a dummy file to ensure the first commit is not empty
                (self.project_root / ".ai_runtime_init").touch()
                self.run_git("add .")
                self.run_git('commit -m "Initial commit"')

            # Ensure main branch exists
            self.run_git(f"checkout -B {self.main_branch}")

    def run_git(self, command: str) -> Dict[str, Any]:
        """Execute git command safely with proper error handling"""
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
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Git command timed out: {command}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def begin_step(self, step_id: int, description: str) -> Dict[str, Any]:
        """Start a new development step with isolated branch"""
        branch_name = f"ai-step-{step_id}"

        # Ensure we're on main branch to start
        self.run_git(f"checkout {self.main_branch}")

        # Create fresh branch for this step
        result = self.run_git(f"checkout -b {branch_name}")

        if result["success"]:
            print(f"🌿 Created branch: {branch_name}")
            return {
                "success": True,
                "branch": branch_name,
                "step_id": step_id
            }
        else:
            return {"success": False, "error": f"Failed to create branch: {result.get('stderr')}"}

    def commit_changes(self, message: str) -> Dict[str, Any]:
        """Commit all current changes"""
        # Check if there are any changes to commit
        status_result = self.run_git("status --porcelain")
        if not status_result["stdout"]:
            return {"success": True, "message": "No changes to commit"}

        self.run_git("add -A")
        commit_result = self.run_git(f'commit -m "{message}"')

        if commit_result["success"]:
            print(f"💾 Committed: {message}")
        else:
            print(f"❌ Commit failed: {commit_result.get('stderr')}")

        return commit_result

    def complete_step(self, step_id: int, success: bool = True) -> Dict[str, Any]:
        """Complete step by merging or discarding changes"""
        branch_name = f"ai-step-{step_id}"
        current_branch = self.get_current_branch()

        if current_branch != branch_name:
            # This can happen if a step had no changes to commit, so we are still on main
            if current_branch == self.main_branch:
                self.run_git(f"branch -D {branch_name}")
                return {"success": True, "action": "merged (no changes)"}
            return {"success": False, "error": f"Not on expected branch {branch_name}, on {current_branch}"}

        if success:
            # Merge changes back to main
            self.run_git(f"checkout {self.main_branch}")
            merge_result = self.run_git(f"merge --no-ff {branch_name}")

            if merge_result["success"]:
                self.run_git(f"branch -d {branch_name}")
                return {"success": True, "action": "merged"}
            else:
                # Merge conflict - abort and clean up
                self.run_git("merge --abort")
                self.run_git(f"checkout {self.main_branch}")
                self.run_git(f"branch -D {branch_name}")
                return {"success": False, "error": "Merge conflict occurred"}
        else:
            # Discard changes - go back to main and delete branch
            self.run_git(f"checkout {self.main_branch}")
            self.run_git(f"branch -D {branch_name}")
            return {"success": True, "action": "discarded"}

    def rollback_step(self, step_id: int) -> Dict[str, Any]:
        """Force rollback of a step"""
        return self.complete_step(step_id, success=False)

    def get_current_branch(self) -> str:
        """Get current branch name"""
        result = self.run_git("branch --show-current")
        return result["stdout"] if result["success"] else "unknown"

    def get_diff(self, filepath: str = "") -> str:
        """Get diff for human review"""
        result = self.run_git(f"diff {filepath}")
        return result.get("stdout", "")

    def get_recent_commits(self, limit: int = 5) -> list:
        """Get recent commit history"""
        result = self.run_git(f"log --oneline -{limit}")
        if result["success"]:
            return result["stdout"].split('\n')
        return []
