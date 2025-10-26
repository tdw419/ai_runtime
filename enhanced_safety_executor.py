"""
ENHANCED SAFETY EXECUTOR - Adds controlled shell execution for system awareness
"""

from pathlib import Path
from typing import Dict, List, Any
import subprocess
import time

from system_state_tracker import state_tracker

class EnhancedSafetyExecutor:
    """
    Enhanced executor with safe shell command execution for system inspection
    """

    def __init__(self):
        self.safe_actions = {"create_file", "run_shell"}  # Added run_shell
        self.restricted_paths = ["..", "/etc", "/bin", "/usr", "/var", "/sys", "/proc"]

        # Whitelist of safe, read-only system inspection commands
        self.safe_commands = {
            "system_info": ["uname -a", "whoami", "pwd"],
            "process_info": ["ps aux", "ps -ef"],
            "disk_info": ["df -h", "du -sh .", "ls -la"],
            "network_info": ["hostname", "ifconfig", "ip addr"],
            "file_exploration": ["find . -maxdepth 2 -type f", "ls -la", "file *"]
        }

        # Absolutely banned command patterns
        self.banned_patterns = [
            "rm", "mv", "chmod", "chown", "kill", "docker",
            "> /dev/", "| bash", "| sh", "curl |", "wget |",
            "format", "mkfs", "dd", "passwd", "useradd"
        ]

    def _is_shell_command_safe(self, command: str) -> bool:
        """Validate that a shell command is safe to execute"""
        command_lower = command.lower()

        # Check against banned patterns
        for banned in self.banned_patterns:
            if banned in command_lower:
                return False

        # Check if it's a known safe command pattern
        for category, safe_cmds in self.safe_commands.items():
            for safe_cmd in safe_cmds:
                if safe_cmd in command_lower:
                    return True

        # Additional safety: only allow commands that start with whitelisted prefixes
        safe_prefixes = ["uname", "whoami", "pwd", "ps ", "df ", "du ", "ls ", "find ", "hostname", "file "]
        if any(command_lower.startswith(prefix) for prefix in safe_prefixes):
            return True

        return False

    def execute_task_plan(self, task_description: str, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute all actions in a plan with comprehensive safety checks.
        Now includes safe shell command execution.
        """
        print(f"    🛡️ Safety-executing {len(plan)} actions for: {task_description}")

        executed_actions = []
        artifacts_created = []
        all_success = True

        for step in plan:
            action_type = step.get("action", "")
            params = step.get("parameters", {})

            # Reject unknown/unsafe actions
            if action_type not in self.safe_actions:
                executed_actions.append({
                    "action": action_type,
                    "success": False,
                    "detail": f"Action '{action_type}' not allowed yet"
                })
                all_success = False
                continue

            # Execute specific action types
            if action_type == "create_file":
                result = self._execute_create_file(params)
                executed_actions.append(result)

                if result["success"] and "filepath" in params:
                    artifacts_created.append(params["filepath"])
                else:
                    all_success = False

            elif action_type == "run_shell":
                result = self._execute_run_shell(params)
                executed_actions.append(result)

                if not result["success"]:
                    all_success = False
                else:
                    # Shell execution success indicates system awareness capability
                    state_tracker.add_capability("system_awareness")
            else:
                executed_actions.append({
                    "action": action_type,
                    "success": False,
                    "detail": f"Unsupported action {action_type}"
                })
                all_success = False

        # Update global system state tracker with what we just did
        if all_success:
            state_tracker.record_task_completion(task_description, artifacts=artifacts_created)
            print(f"    ✅ Task completed successfully: {task_description}")
        else:
            state_tracker.record_task_failure(task_description, "Some actions failed")
            print(f"    ⚠️ Task partially failed: {task_description}")

        return {
            "success": all_success,
            "executed_actions": executed_actions,
            "artifacts_created": artifacts_created
        }

    def _execute_create_file(self, params: Dict) -> Dict[str, Any]:
        """Safely create a file"""
        filepath = params.get("filepath", "")
        content = params.get("content", "")

        # Safety check path
        if not filepath or not self._is_path_safe(filepath):
            return {
                "action": "create_file",
                "success": False,
                "detail": f"Unsafe or invalid path: {filepath}"
            }

        # Actually try to write file
        try:
            path_obj = Path(filepath)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(content)

            print(f"      📄 Created: {filepath} ({len(content)} bytes)")

            return {
                "action": "create_file",
                "success": True,
                "detail": f"File created at {filepath}"
            }

        except Exception as e:
            return {
                "action": "create_file",
                "success": False,
                "detail": f"Exception while writing file: {str(e)}"
            }

    def _execute_run_shell(self, params: Dict) -> Dict[str, Any]:
        """Execute shell command with comprehensive safety checks"""
        command = params.get("command", "")

        # Validate command safety
        if not self._is_shell_command_safe(command):
            return {
                "action": "run_shell",
                "success": False,
                "detail": f"Command failed safety check: {command}"
            }

        # Actually execute the command with safety limits
        try:
            print(f"      🖥️  Executing safe command: {command}")

            # Execute with timeout and output limits
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd="."  # Current directory only
            )

            output = result.stdout.strip() if result.stdout else ""
            error = result.stderr.strip() if result.stderr else ""

            if result.returncode == 0:
                detail = f"Command succeeded: {command}"
                if output:
                    detail += f"\\nOutput: {output[:200]}{'...' if len(output) > 200 else ''}"

                # Learn from successful system inspection
                if "uname" in command:
                    state_tracker.add_capability("system_identification")
                if "ps" in command:
                    state_tracker.add_capability("process_inspection")
                if "df" in command or "du" in command:
                    state_tracker.add_capability("resource_monitoring")

                return {
                    "action": "run_shell",
                    "success": True,
                    "detail": detail,
                    "output": output
                }
            else:
                return {
                    "action": "run_shell",
                    "success": False,
                    "detail": f"Command failed (exit {result.returncode}): {error}"
                }

        except subprocess.TimeoutExpired:
            return {
                "action": "run_shell",
                "success": False,
                "detail": "Command timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "action": "run_shell",
                "success": False,
                "detail": f"Exception executing command: {str(e)}"
            }

    def _is_path_safe(self, filepath: str) -> bool:
        """Validate that a file path is safe to write to"""
        if any(bad in filepath for bad in self.restricted_paths):
            return False
        if filepath.startswith("/"):
            return False
        if ".." in filepath:
            return False
        return True

# Enhanced global executor instance
enhanced_safety_executor = EnhancedSafetyExecutor()
