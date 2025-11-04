import os
import glob
import subprocess
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProjectState:
    path: str
    exists: bool
    git_status: str = "unknown"
    recent_changes: List[str] = None
    dependency_count: int = 0
    test_status: str = "unknown"
    build_status: str = "unknown"
    error_count: int = 0
    loc_count: int = 0  # Lines of code
    file_count: int = 0  # Number of Python files

class ProjectMonitor:
    def __init__(self, config):
        self.config = config
        self.watched_projects = config.get("projects", [])
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        import logging
        logger = logging.getLogger('project_monitor')
        return logger
    
    async def scan_all_projects(self) -> Dict[str, ProjectState]:
        """Scan all configured projects"""
        results = {}
        for project_config in self.watched_projects:
            project_path = project_config.get("path")
            if project_path:
                state = await self.scan_project(project_path)
                results[project_path] = state
        return results
    
    async def scan_project(self, project_path: str) -> ProjectState:
        """Comprehensive project analysis"""
        project_path = os.path.expanduser(project_path)
        state = ProjectState(path=project_path, exists=os.path.exists(project_path))
        
        if not state.exists:
            return state
        
        # Run all checks in parallel
        await asyncio.gather(
            self._check_git_status(state),
            self._check_recent_changes(state),
            self._analyze_dependencies(state),
            self._check_test_status(state),
            self._check_code_quality(state),  # New: code quality check
            return_exceptions=True
        )
        
        return state
    
    async def _check_code_quality(self, state: ProjectState):
        """Check code quality metrics"""
        try:
            # Count lines of code in Python files
            python_files = list(Path(state.path).rglob("*.py"))
            state.loc_count = sum(self._count_lines(f) for f in python_files)
            state.file_count = len(python_files)
        except:
            state.loc_count = 0
            state.file_count = 0
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file"""
        try:
            with open(file_path, 'r') as f:
                return len(f.readlines())
        except:
            return 0
    
    async def _check_git_status(self, state: ProjectState):
        """Get git status"""
        try:
            if os.path.exists(os.path.join(state.path, '.git')):
                result = subprocess.run(
                    ["git", "-C", state.path, "status", "--porcelain"],
                    capture_output=True, text=True, timeout=10
                )
                state.git_status = "clean" if not result.stdout.strip() else "dirty"
            else:
                state.git_status = "no_git"
        except Exception as e:
            state.git_status = f"error: {str(e)}"
    
    async def _check_recent_changes(self, state: ProjectState):
        """Get recent file changes (last 24 hours)"""
        try:
            result = subprocess.run(
                ["find", state.path, "-name", "*.py", "-mtime", "-1", "-type", "f"],
                capture_output=True, text=True, timeout=30
            )
            state.recent_changes = [f for f in result.stdout.strip().split('\n') if f]
        except Exception as e:
            state.recent_changes = []
            state.error_count += 1
    
    async def _analyze_dependencies(self, state: ProjectState):
        """Count dependencies in requirements.txt or pyproject.toml"""
        try:
            req_file = os.path.join(state.path, "requirements.txt")
            if os.path.exists(req_file):
                with open(req_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    state.dependency_count = len(lines)
            else:
                state.dependency_count = 0
        except Exception as e:
            state.dependency_count = 0
            state.error_count += 1
    
    async def _check_test_status(self, state: ProjectState):
        """Check if tests are passing"""
        try:
            # Simple check for test files existence
            test_files = list(Path(state.path).rglob("test_*.py")) + list(Path(state.path).rglob("*_test.py"))
            state.test_status = "has_tests" if test_files else "no_tests"
        except Exception as e:
            state.test_status = "error"
            state.error_count += 1
