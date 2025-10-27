# task_registry.py
"""
Central registry of operational tasks the AI steward can perform.
All tasks are read-only/safe by default.
"""

TASK_REGISTRY = {
    "system_health_audit": {
        "name": "System Health Audit",
        "aliases": ["check health", "health check", "system audit"],
        "description": "Comprehensive system health check and resource analysis",
        "phase": "stewardship",
        "priority": "high",
        "estimated_duration": "2 minutes",
        "schedule": "daily",
        "conditions": ["high_memory_usage", "high_disk_usage", "on_demand"],
        "implementation": [
            "Check disk space usage and identify large directories if >85% full",
            "Analyze memory pressure and top consuming processes",
            "Verify critical services are running",
            "Review recent system anomalies",
            "Generate health summary section in STATUS.md"
        ],
        "success_criteria": ["disk_space_checked", "memory_analyzed", "health_reported"]
    },

    "security_baseline_update": {
        "name": "Update Security Baseline",
        "description": "Refresh system behavior baseline for anomaly detection",
        "phase": "security",
        "priority": "medium",
        "schedule": "weekly",
        "conditions": ["baseline_stale", "on_demand"],
        "implementation": [
            "Capture current process baseline",
            "Update network connection patterns",
            "Refresh resource usage thresholds",
            "Persist updated baseline to ai_os_state.json"
        ],
        "success_criteria": ["baseline_updated", "patterns_captured"]
    },

    "critical_service_check": {
        "name": "Critical Service Health Check",
        "description": "Verify essential services are running and stable",
        "phase": "reliability",
        "priority": "high",
        "schedule": "every_cycle",
        "conditions": ["always_recommended"],
        "implementation": [
            "Check critical_services list from ai_os_state.json",
            "Match running processes against service patterns",
            "Generate service health section in STATUS.md",
            "Report unstable or missing services"
        ],
        "success_criteria": ["services_checked", "status_reported"]
    },

    "restart_service_test": {
        "name": "Restart Service Test",
        "description": "Test task that should trigger escalation",
        "priority": "medium",
        "schedule": "on_demand",
        "conditions": [],
        "implementation": [
            "Check service status",
            "restart unstable service if needed",
            "Verify service recovered"
        ],
        "success_criteria": []
    }
}
