"""
System Stewardship Monitor - Protects the integrity and security of the AI OS.
"""

import os
import psutil
import hashlib
from pathlib import Path
from typing import Dict, List, Any

class SystemStewardshipMonitor:
    """
    Monitors the system for anomalies, security events, and deviations from baseline.
    """
    def __init__(self):
        self.baseline_established = False
        self.file_baseline: Dict[Path, str] = {}
        self.process_baseline: set = set()
        self.security_events: List[Dict[str, Any]] = []

    def _hash_file(self, filepath: Path) -> str:
        """Computes the SHA256 hash of a file."""
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (IOError, OSError):
            return ""

    def collect_system_baseline(self):
        """
        Establishes a baseline of the current system state, including file hashes
        and running processes.
        """
        print("🛡️ Collecting system baseline...")
        # Baseline critical files
        critical_files = [Path(p) for p in [
            "operational_ai_os_bootstrapper.py",
            "enhanced_safety_executor.py",
            "system_state_tracker.py",
            "action_handler.py",
            "ai_os_roadmap_evolver.py",
            "roadmap_processor.py",
            "system_stewardship_monitor.py"
        ]]

        for f in critical_files:
            if f.exists():
                self.file_baseline[f] = self._hash_file(f)

        # Baseline running processes
        self.process_baseline = {p.name() for p in psutil.process_iter(['name'])}
        self.baseline_established = True
        print(f"  Baseline established with {len(self.file_baseline)} files and {len(self.process_baseline)} processes.")

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detects deviations from the established baseline.
        """
        if not self.baseline_established:
            return [{"type": "warning", "message": "Baseline not established. Cannot detect anomalies."}]

        anomalies = []

        # 1. Check for file modifications
        for f, baseline_hash in self.file_baseline.items():
            if not f.exists():
                anomaly = {"type": "file_deleted", "file": str(f)}
                anomalies.append(anomaly)
                self.security_events.append(anomaly)
                continue

            current_hash = self._hash_file(f)
            if current_hash != baseline_hash:
                anomaly = {"type": "file_modified", "file": str(f), "old_hash": baseline_hash, "new_hash": current_hash}
                anomalies.append(anomaly)
                self.security_events.append(anomaly)

        # 2. Check for unexpected new processes
        current_processes = {p.name() for p in psutil.process_iter(['name'])}
        new_processes = current_processes - self.process_baseline
        if new_processes:
            for proc_name in new_processes:
                anomaly = {"type": "new_process_detected", "process_name": proc_name}
                anomalies.append(anomaly)
                self.security_events.append(anomaly)

        return anomalies

    def generate_security_report(self) -> str:
        """
        Generates a human-readable security report based on collected events.
        """
        report = ["# System Stewardship Security Report"]
        report.append(f"Generated at: {__import__('datetime').datetime.now().isoformat()}")
        report.append(f"Total Security Events Logged: {len(self.security_events)}")

        if not self.security_events:
            report.append("\n✅ No significant security events detected.")
            return "\n".join(report)

        report.append("\n## Logged Events:")
        for event in self.security_events:
            event_type = event.get("type", "unknown").replace("_", " ").title()
            details = ", ".join(f"{k}: {v}" for k, v in event.items() if k != 'type')
            report.append(f"- **{event_type}**: {details}")

        return "\n".join(report)

system_monitor = SystemStewardshipMonitor()
