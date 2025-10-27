# task_scheduler.py
"""
TaskScheduler: decides what should be done next and why.
Phase 3.1: Proactive recommendations in STATUS.md.

It looks at:
- system_state (memory, disk, baseline age, etc.)
- task_history (when tasks last ran)
- each task's declared conditions and schedule

Then it produces human-readable recommendations.
"""

import time
from typing import Dict, List
from task_registry import TASK_REGISTRY

# Lower number = higher priority in sorting
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

class TaskScheduler:
    def __init__(self, state_tracker):
        """
        state_tracker: SystemStateTracker
        We don't snapshot state here because we want fresh reads on demand.
        """
        self.state_tracker = state_tracker

    def _get_task_history(self) -> Dict[str, Dict]:
        state = self.state_tracker.get_state()
        return state.get("task_history", {})

    def _get_system_state(self) -> Dict[str, float]:
        return self.state_tracker.get_system_state()

    def _should_recommend(self, task_id: str, task: Dict, task_history: Dict[str, Dict], system_state: Dict[str, float]) -> bool:
        """
        Decide if this task should be surfaced in Recommended Actions.
        This is deliberately conservative. We don't spam.
        """
        now = time.time()
        last_run = task_history.get(task_id, {}).get("last_run", 0)

        # --- cooldown ---
        # Never recommend a task that just ran in the last 5 minutes
        if now - last_run < 300:
            return False

        # --- schedule backing ---
        schedule = task.get("schedule", "on_demand")

        if schedule == "daily" and (now - last_run) < 86400:
            # ran in last 24h → not urgent unless conditions force it
            pass
        elif schedule == "weekly" and (now - last_run) < 604800:
            pass
        # (on_demand/every_cycle always allowed to show)

        # --- condition checks ---
        conditions = task.get("conditions", [])

        # memory pressure
        if "high_memory_usage" in conditions:
            mem = system_state.get("memory_usage", 0)
            if mem >= 85:  # high memory
                return True

        # disk pressure
        if "high_disk_usage" in conditions:
            disk = system_state.get("disk_usage", 0)
            if disk >= 85:
                return True

        # baseline staleness
        if "baseline_stale" in conditions:
            baseline_ts = system_state.get("baseline_updated_ts", 0)
            # older than 1 week
            if (now - baseline_ts) > 604800:
                return True

        # always_recommended tasks are always surfaced
        if "always_recommended" in conditions:
            return True

        # on_demand tasks:
        # we still allow them to show as "you can run me" if nothing else is urgent,
        # but to avoid clutter we don't default True here. We'll handle it in discover().
        if "on_demand" in conditions:
            return False

        return False

    def _reason_for_task(self, task: Dict, system_state: Dict[str, float]) -> str:
        """
        Generate a human-readable "Why this matters" string.
        """
        reasons = []
        mem = system_state.get("memory_usage", 0)
        disk = system_state.get("disk_usage", 0)
        baseline_ts = system_state.get("baseline_updated_ts", 0)
        now = time.time()

        if "high_memory_usage" in task.get("conditions", []) and mem >= 85:
            reasons.append(f"Memory usage is {mem:.0f}%")

        if "high_disk_usage" in task.get("conditions", []) and disk >= 85:
            reasons.append(f"Disk usage is {disk:.0f}%")

        if "baseline_stale" in task.get("conditions", []) and (now - baseline_ts) > 604800:
            reasons.append("Security baseline is over 1 week old")

        if "always_recommended" in task.get("conditions", []):
            reasons.append("Essential reliability check")

        if not reasons:
            return "Scheduled maintenance / good hygiene"

        return "; ".join(reasons)

    def discover_recommendations(self) -> List[Dict]:
        """
        Returns a sorted list of tasks to recommend, annotated with reason.
        """
        system_state = self._get_system_state()
        task_history = self._get_task_history()

        recs = []
        for task_id, task in TASK_REGISTRY.items():
            if self._should_recommend(task_id, task, task_history, system_state):
                recs.append({
                    "id": task_id,
                    "name": task["name"],
                    "priority": task.get("priority", "medium"),
                    "description": task.get("description", ""),
                    "reason": self._reason_for_task(task, system_state),
                })

        # If nothing triggered urgently, offer 1 safe on-demand task so the dashboard
        # never feels "empty"
        if not recs:
            # pick first high-priority on-demand style task as a gentle suggestion
            fallback_candidates = []
            for task_id, task in TASK_REGISTRY.items():
                if "on_demand" in task.get("conditions", []):
                    fallback_candidates.append({
                        "id": task_id,
                        "name": task["name"],
                        "priority": task.get("priority", "medium"),
                        "description": task.get("description", ""),
                        "reason": "Available on demand",
                    })
            # pick highest priority
            fallback_candidates.sort(
                key=lambda x: _PRIORITY_ORDER.get(x["priority"], 99)
            )
            if fallback_candidates:
                recs.append(fallback_candidates[0])

        # sort recs by priority (high first)
        recs.sort(key=lambda x: _PRIORITY_ORDER.get(x["priority"], 99))
        return recs

    def format_recommendations_md(self) -> str:
        """
        Return a full markdown section for STATUS.md.
        """
        recs = self.discover_recommendations()

        if not recs:
            # extremely defensive fallback
            return (
                "## Recommended Actions\n\n"
                "System is stable. No immediate actions recommended.\n"
            )

        out_lines = []
        out_lines.append("## Recommended Actions\n")

        for rec in recs:
            icon = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🔵"
            out_lines.append(f"{icon} **{rec['name']}**")
            out_lines.append(f"- *Why:* {rec['reason']}")
            out_lines.append(f"- *Description:* {rec['description']}\n")

        out_lines.append("*Run with:* `run_task <task_id>`\n")
        out_lines.append("For example: `run_task system_health_audit`\n")

        return "\n".join(out_lines)
