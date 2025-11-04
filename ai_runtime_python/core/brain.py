"""Decision engine for the AI daemon."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

from .memory import ExperienceDB
from .llm_manager import LLMManager
from .action_parser import ActionParser
from .safety_guard import SafetyGuard
from .system_prompts import SYSTEM_ADMIN_PROMPT


class AIBrain:
    """Rule-driven and LLM-enhanced decision engine."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.thresholds = (self.config.get("system") or {}).get("thresholds", {})
        self.work_hours = (self.config.get("system") or {}).get("work_hours", {})
        
        llm_config = (self.config.get("system") or {}).get("lm_studio", {})
        self.llm_manager = LLMManager(
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model")
        )
        self.action_parser = ActionParser()
        self.safety_guard = SafetyGuard()

    async def make_decision(self, telemetry: Dict[str, Any], memory_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return the next action the daemon should take, combining rules and LLM."""
        # 1. Evaluate rule-based decisions first for speed and efficiency
        rule_decision = self._evaluate_rules(telemetry, memory_context)

        # 2. If rules don't produce a high-confidence decision, consult the LLM
        if rule_decision.get("confidence", 0.0) < 0.7:
            llm_recommendation = await self.get_system_recommendation(telemetry, memory_context)
            if llm_recommendation and self.safety_guard.validate(llm_recommendation):
                # If the LLM provides a valid and safe action, prioritize it
                return llm_recommendation

        # 3. Fallback to the rule-based decision
        return rule_decision

    async def get_system_recommendation(self, telemetry: Dict[str, Any], context: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Ask LM Studio what to do with the current system state."""
        prompt = self._build_system_prompt(telemetry, context)
        
        try:
            llm_response = await self.llm_manager.query(prompt, system_prompt=SYSTEM_ADMIN_PROMPT)
            if llm_response:
                return self.action_parser.parse(llm_response)
        except Exception as e:
            print(f"Error querying LLM: {e}") # Replace with proper logging
        return None

    def _build_system_prompt(self, telemetry: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """Builds a detailed prompt for the LLM based on current state."""
        # This can be expanded to be much more detailed
        telemetry_summary = json.dumps(telemetry, indent=2)
        recent_events = json.dumps(context, indent=2)
        
        return (
            f"Current Telemetry:\n{telemetry_summary}\n\n"
            f"Recent Events:\n{recent_events}"
        )

    def _evaluate_rules(self, state: Dict[str, Any], context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Keeps the original rule-based logic."""
        decisions: List[Dict[str, Any]] = []

        resource_decision = self._resource_protection(state)
        if resource_decision:
            decisions.append(resource_decision)

        presence_decision = self._workspace_presence()
        if presence_decision:
            decisions.append(presence_decision)

        security_decision = self._security_watch(context)
        if security_decision:
            decisions.append(security_decision)

        if not decisions:
            return {"action": "noop", "confidence": 0.0}

        decisions.sort(key=lambda item: item.get("confidence", 0.0), reverse=True)
        return decisions[0]

    async def update_models(self, patterns: Dict[str, Any]) -> None:
        """Update internal models based on learned patterns (placeholder)."""
        await asyncio.sleep(0)

    def _resource_protection(self, state: Dict[str, Any]) -> Dict[str, Any]:
        alerts = []
        for key in ("cpu", "memory", "disk"):
            metric_key = f"{key}_percent" if key != "cpu" else "cpu_percent"
            value = state.get(metric_key)
            if value is None:
                continue
            thresholds = self.thresholds.get(key, {})
            warning = thresholds.get("warning", 100)
            critical = thresholds.get("critical", 100)
            severity = None
            if value >= critical:
                severity = "critical"
            elif value >= warning:
                severity = "warning"
            if severity:
                alerts.append(
                    {
                        "resource": key,
                        "value": value,
                        "severity": severity,
                        "action": thresholds.get("action", "notify"),
                    }
                )

        if not alerts:
            return {}

        return {
            "action": "trigger_workflow",
            "workflow_type": "system_optimization",
            "confidence": 0.85,
            "payload": {
                "issue": "resource_pressure",
                "alerts": alerts,
                "observed_at": datetime.utcnow().isoformat(),
            },
        }

    def _workspace_presence(self) -> Dict[str, Any]:
        if not self.work_hours:
            return {}
        start = self.work_hours.get("start")
        end = self.work_hours.get("end")
        if not start or not end:
            return {}

        now = datetime.now().strftime("%H:%M")
        if start <= now <= end:
            return {
                "action": "trigger_workflow",
                "workflow_type": "workspace_setup",
                "confidence": 0.75,
                "payload": {
                    "event": "user_active_window",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }
        return {}

    def _security_watch(self, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not context:
            return {}
        suspicious = [entry for entry in context if entry.get("type") == "security_alert"]
        if not suspicious:
            return {}
        return {
            "action": "trigger_workflow",
            "workflow_type": "security_response",
            "confidence": 0.8,
            "payload": {
                "alerts": suspicious,
                "observed_at": datetime.utcnow().isoformat(),
            },
        }
