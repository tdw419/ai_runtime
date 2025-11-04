"""System monitoring utilities for the AI daemon."""
import asyncio
from datetime import datetime
from typing import Any, Dict, Tuple

import psutil


class SystemMonitor:
    """Collects metrics and evaluates critical conditions."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.thresholds = (self.config.get("system") or {}).get("thresholds", {})

    async def capture_system_state(self) -> Dict[str, Any]:
        """Gather system metrics asynchronously."""
        loop = asyncio.get_running_loop()
        cpu = await loop.run_in_executor(None, psutil.cpu_percent, 1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        temps = self._safe_temperatures()

        processes = self._top_processes(limit=5)
        app_metrics = await self.collect_application_metrics()

        state = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "temperature_c": temps,
            "top_processes": processes,
        }
        if app_metrics:
            state["application_metrics"] = app_metrics
        return state

    def is_critical(self, state: Dict[str, Any]) -> bool:
        """Evaluate whether any metric exceeds critical thresholds."""
        entries = (
            ("cpu", state.get("cpu_percent")),
            ("memory", state.get("memory_percent")),
            ("disk", state.get("disk_percent")),
            ("temperature", (state.get("temperature_c") or {}).get("max")),
        )
        for key, value in entries:
            if value is None:
                continue
            threshold = self.thresholds.get(key, {})
            if value >= threshold.get("critical", 101):
                return True
        return False

    async def collect_application_metrics(self) -> Dict[str, Any]:
        """Collect metrics for user-defined applications."""
        metrics: Dict[str, Any] = {}
        services_cfg = self.config.get("services") or {}
        app_cfg = services_cfg.get("applications") or []
        if not isinstance(app_cfg, list):
            return metrics

        for app in app_cfg:
            name = app.get("name")
            process_names = app.get("process_names") or []
            if not name or not process_names:
                continue
            metrics[name] = self._aggregate_process_metrics(process_names)
        return metrics

    def _safe_temperatures(self) -> Dict[str, float]:
        temps: Dict[str, float] = {}
        try:
            sensors = psutil.sensors_temperatures()
        except (AttributeError, NotImplementedError):
            return temps
        if not sensors:
            return temps

        readings = [entry.current for values in sensors.values() for entry in values if entry.current is not None]
        if readings:
            temps["max"] = max(readings)
            temps["avg"] = sum(readings) / len(readings)
        return temps

    def _top_processes(self, limit: int = 5) -> Dict[str, Tuple[int, float]]:
        """Return the top processes by CPU usage."""
        processes: Dict[str, Tuple[int, float]] = {}
        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
                info = proc.info
                name = info.get("name") or "unknown"
                processes[name] = (
                    info.get("pid") or -1,
                    info.get("cpu_percent") or 0.0,
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return dict(sorted(processes.items(), key=lambda item: item[1][1], reverse=True)[:limit])

    def _aggregate_process_metrics(self, process_names) -> Dict[str, Any]:
        """Aggregate CPU and memory metrics for named processes."""
        cpu_total = 0.0
        rss_total = 0
        matched = 0

        try:
            for proc in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
                if proc.info.get("name") not in process_names:
                    continue
                matched += 1
                cpu_total += proc.info.get("cpu_percent") or 0.0
                mem_info = proc.info.get("memory_info")
                if mem_info:
                    rss_total += getattr(mem_info, "rss", 0)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

        return {
            "process_count": matched,
            "cpu_percent_total": round(cpu_total, 2),
            "rss_mb_total": round(rss_total / (1024 * 1024), 2),
        }
