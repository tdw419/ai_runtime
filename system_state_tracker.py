# system_state_tracker.py
import json
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

class SystemStateTracker:
    """
    Tracks real system state across sessions - the fuel for roadmap evolution
    """

    def __init__(self, state_file: str = ".ai_runtime/state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(exist_ok=True, parents=True)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load persisted system state"""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except:
                pass

        # Initial state
        return {
            "completed_tasks": [],
            "failed_tasks": [],
            "artifacts_created": [],
            "capabilities": [],
            "bottlenecks": [],
            "process_lifetimes": {},
            "critical_services": [],
            "service_status_history": {},
            "metrics": {
                "total_cycles": 0,
                "successful_tasks": 0,
                "failed_attempts": 0,
                "files_created": 0
            },
            "last_updated": datetime.now().isoformat()
        }

    def save_state(self):
        """Persist current state"""
        self.state["last_updated"] = datetime.now().isoformat()
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def record_task_completion(self, task_description: str, artifacts: List[str] = None):
        """Record a successfully completed task"""
        if task_description not in self.state["completed_tasks"]:
            self.state["completed_tasks"].append(task_description)

        if artifacts:
            for artifact in artifacts:
                if artifact not in self.state["artifacts_created"]:
                    self.state["artifacts_created"].append(artifact)
                    self.state["metrics"]["files_created"] += 1

        self.state["metrics"]["successful_tasks"] += 1
        self._update_capabilities_from_task(task_description)
        self.save_state()

    def record_task_failure(self, task_description: str, error: str = ""):
        """Record a failed task attempt"""
        failure_record = {
            "task": task_description,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

        if failure_record not in self.state["failed_tasks"]:
            self.state["failed_tasks"].append(failure_record)

        self.state["metrics"]["failed_attempts"] += 1

        # Track bottlenecks from repeated failures
        similar_failures = [f for f in self.state["failed_tasks"] if f["task"] == task_description]
        if len(similar_failures) >= 2:
            bottleneck = f"Repeated failures on: {task_description}"
            if bottleneck not in self.state["bottlenecks"]:
                self.state["bottlenecks"].append(bottleneck)

        self.save_state()

    def record_cycle_completion(self):
        """Record that a cycle completed"""
        self.state["metrics"]["total_cycles"] += 1
        self.save_state()

    def _update_capabilities_from_task(self, task_description: str):
        """Extract capabilities from completed tasks"""
        task_lower = task_description.lower()
        new_capabilities = []

        capability_map = {
            "shell": "command_execution",
            "command": "command_execution",
            "process": "process_management",
            "environment": "environment_management",
            "virtual": "virtualization",
            "emulation": "emulation",
            "config": "configuration_management",
            "logging": "logging_monitoring",
            "test": "testing",
            "api": "api_integration",
            "network": "networking",
            "storage": "storage_management"
        }

        for keyword, capability in capability_map.items():
            if keyword in task_lower and capability not in self.state["capabilities"]:
                new_capabilities.append(capability)

        self.state["capabilities"].extend(new_capabilities)
        # Remove duplicates while preserving order
        self.state["capabilities"] = list(dict.fromkeys(self.state["capabilities"]))

    def get_system_state(self) -> Dict[str, Any]:
        """Get comprehensive system state for roadmap evolution"""
        return {
            "completed_tasks": self.state["completed_tasks"],
            "failed_tasks": [f["task"] for f in self.state["failed_tasks"]],
            "artifacts_created": self.state["artifacts_created"],
            "capabilities": self.state["capabilities"],
            "bottlenecks": self.state["bottlenecks"],
            "metrics": self.state["metrics"],
            "capability_tier": self._assess_capability_tier(),
            "has_config": any("config" in cap for cap in self.state["capabilities"]),
            "has_logging": any("logging" in cap for cap in self.state["capabilities"]),
            "has_testing": any("testing" in cap for cap in self.state["capabilities"]),
            "total_artifacts": len(self.state["artifacts_created"])
        }

    def _assess_capability_tier(self) -> str:
        """Assess current capability tier based on actual achievements"""
        capabilities = self.state["capabilities"]
        completed_count = len(self.state["completed_tasks"])

        if completed_count >= 10 and any(cap in capabilities for cap in ["virtualization", "emulation"]):
            return "ADVANCED"
        elif completed_count >= 5 and any(cap in capabilities for cap in ["process_management", "environment_management"]):
            return "ENHANCED"
        elif completed_count >= 2:
            return "BASIC"
        else:
            return "INITIAL"

# Global tracker
state_tracker = SystemStateTracker()
