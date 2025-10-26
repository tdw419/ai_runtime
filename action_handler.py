"""
Action Handler - Prepares and validates AI-generated action plans for execution.
"""

from typing import Dict, List, Any

class ActionHandler:
    """
    Handles the preparation and safety filtering of AI-generated action plans.
    """
    def __init__(self):
        # Define a set of actions that are currently considered safe and implemented.
        self.allowed_actions = {"create_file", "run_shell"}

    def prepare_actions(self, task_description: str, ai_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a raw AI-generated plan and prepares it for the safety executor.

        This involves:
        1. Filtering out any actions that are not allowed or recognized.
        2. Potentially validating parameters in the future.
        3. Ensuring the plan is in the correct format.

        Args:
            task_description: The description of the task the plan is for.
            ai_plan: A list of action dictionaries from the AI.

        Returns:
            A sanitized list of action dictionaries ready for execution.
        """
        print(f"    🔎 Preparing actions for: {task_description}")
        if not isinstance(ai_plan, list):
            print("      ⚠️  Warning: AI plan was not a list, returning empty plan.")
            return []

        safe_plan = []
        for action in ai_plan:
            action_type = action.get("action")
            if action_type in self.allowed_actions:
                safe_plan.append(action)
            else:
                print(f"      - Action '{action_type}' is not allowed and has been filtered out.")

        print(f"    - Prepared {len(safe_plan)} safe actions from an initial {len(ai_plan)}.")
        return safe_plan

# Global instance to be used by other modules.
action_handler = ActionHandler()
