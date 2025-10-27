# task_runner.py
"""
TaskRunner: maps natural language commands to a known task using deterministic aliases.
Phase 3.2: Natural language control for the steward.
"""

from typing import Dict, Optional
from task_registry import TASK_REGISTRY

class TaskRunner:
    def __init__(self, task_executor):
        self.task_executor = task_executor
        self.task_map = self._build_task_map()

    def _build_task_map(self) -> Dict[str, str]:
        """Create a deterministic mapping from names and aliases to task IDs."""
        mapping = {}
        for task_id, task in TASK_REGISTRY.items():
            # Add the name (lowercase)
            mapping[task['name'].lower()] = task_id
            # Add the task_id itself
            mapping[task_id.lower()] = task_id
            # Add all aliases
            for alias in task.get('aliases', []):
                mapping[alias.lower()] = task_id
        return mapping

    def find_task(self, user_input: str) -> Optional[str]:
        """Find the task ID for the user input using a direct lookup."""
        # Normalize input
        user_input_lower = user_input.lower().strip()

        # Check for common prefixes
        for prefix in ["run ", "execute ", "start "]:
            if user_input_lower.startswith(prefix):
                user_input_lower = user_input_lower[len(prefix):]
                break

        return self.task_map.get(user_input_lower)

    def run_from_text(self, user_input: str) -> Dict:
        """Interpret the user's message and run the corresponding task."""
        task_id = self.find_task(user_input)

        if not task_id:
            return {
                "success": False,
                "error": "I couldn't map that request to a known task.",
                "hint": "Try 'list_tasks' or 'run_task system_health_audit'"
            }

        # We found a match. Delegate to executor.
        result = self.task_executor.execute_task(task_id)

        # Add interpretation info for transparency
        task_def = TASK_REGISTRY.get(task_id, {})
        result["interpreted_task_id"] = task_id
        result["interpreted_task_name"] = task_def.get("name", task_id)
        result["match_score"] = 100 # Deterministic match
        return result
