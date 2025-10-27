# collaboration_manager.py
"""
CollaborationManager: Tracks escalations where the steward needs human input.
Phase 3.3: Human-AI collaboration and decision persistence.
"""

import json
import os
import time
from typing import Dict, List, Optional

class CollaborationManager:
    def __init__(self, data_file="collaboration/escalations.json"):
        self.data_file = data_file
        self.escalations = {}
        self._ensure_data_dir()
        self._load_escalations()

    def _ensure_data_dir(self):
        """Create collaboration directory if it doesn't exist."""
        dir_name = os.path.dirname(self.data_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _load_escalations(self):
        """Load existing escalations from disk."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.escalations = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.escalations = {}
        else:
            self.escalations = {}

    def _save_escalations(self):
        """Save escalations to disk."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.escalations, f, indent=2)
        except IOError:
            # If we can't save, keep in memory only
            pass

    def create_escalation(self, task_id: str, step_description: str,
                         reason: str, context: Dict) -> str:
        """
        Create a new escalation record.
        Returns escalation ID for reference.
        """
        escalation_id = f"esc_{int(time.time())}_{hash(step_description) % 10000:04d}"

        self.escalations[escalation_id] = {
            "task_id": task_id,
            "step_description": step_description,
            "reason": reason,
            "context": context,
            "created_at": time.time(),
            "status": "pending",  # pending, approved, denied, resolved
            "human_guidance": None,
            "resolved_at": None
        }

        self._save_escalations()
        return escalation_id

    def get_pending_escalations(self) -> Dict[str, Dict]:
        """Get all escalations waiting for human input."""
        return {eid: esc for eid, esc in self.escalations.items()
                if esc.get("status") == "pending"}

    def resolve_escalation(self, escalation_id: str, human_guidance: str,
                          status: str = "approved") -> bool:
        """
        Resolve an escalation with human guidance.
        Status: approved, denied, or resolved
        """
        if escalation_id not in self.escalations:
            return False

        self.escalations[escalation_id].update({
            "status": status,
            "human_guidance": human_guidance,
            "resolved_at": time.time()
        })

        self._save_escalations()
        return True

    def get_escalation(self, escalation_id: str) -> Optional[Dict]:
        """Get a specific escalation by ID."""
        return self.escalations.get(escalation_id)

    def format_escalations_md(self) -> str:
        """Format pending escalations for STATUS.md."""
        pending = self.get_pending_escalations()
        if not pending:
            return ""

        md = "## 🤝 Human-AI Collaboration\n\n"
        md += "*The steward is waiting for your input on these items:*\n\n"

        for eid, esc in pending.items():
            md += f"### 🟠 {esc['task_id']}\n"
            md += f"- **Step**: {esc['step_description']}\n"
            md += f"- **Reason**: {esc['reason']}\n"
            md += f"- **Escalation ID**: `{eid}`\n\n"
            md += "*To resolve:* `resolve_escalation {eid} \"your guidance here\"`\n\n"

        return md
