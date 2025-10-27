# system_state_tracker.py
"""
Persistent state management for the AI runtime steward.
Tracks system baselines, task history, and operational state across restarts.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

class SystemStateTracker:
    def __init__(self, state_file: str = "ai_os_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load persistent state from disk, creating default if missing"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                # Corrupted state file, start fresh
                pass

        # Default state structure
        return {
            "system_info": {
                "phase": "bootstrap",
                "capability_tier": 0,
                "last_health_check": None,
                "baseline_updated_ts": 0
            },
            "task_history": {},
            "learned_policies": {},
            "critical_services": [],
            "collaboration_sessions": []
        }

    def get_state(self) -> Dict[str, Any]:
        """Return the complete state"""
        return self.state

    def update_state(self, new_state: Dict[str, Any]):
        """Update state with new values (merge, not replace)"""
        self.state.update(new_state)
        self._save_state()

    def update_task_history(self, task_id: str, success: bool, result: str):
        """Update task execution history"""
        if "task_history" not in self.state:
            self.state["task_history"] = {}

        self.state["task_history"][task_id] = {
            "last_run": time.time(),
            "success": success,
            "result": result
        }
        self._save_state()

    def get_system_state(self) -> Dict[str, Any]:
        """Get current system state for scheduling decisions"""
        # This will be enhanced with real system metrics later
        return {
            "memory_usage": self._get_memory_usage(),
            "disk_usage": self._get_disk_usage(),
            "baseline_updated_ts": self.state["system_info"].get("baseline_updated_ts", 0),
            "phase": self.state["system_info"].get("phase", "bootstrap")
        }

    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            # Fallback without psutil
            return 50.0  # Default assumption

    def _get_disk_usage(self) -> float:
        """Get current disk usage percentage"""
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            # Fallback without psutil
            return 60.0  # Default assumption

    def _save_state(self):
        """Persist state to disk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save state: {e}")

# Global instance for easy access
state_tracker = SystemStateTracker()
