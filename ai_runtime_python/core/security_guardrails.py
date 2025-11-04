import asyncio
from typing import Dict, List, Optional
import os
import shlex

class SecurityGuardrails:
    """High-assurance security guardrails for LLM output validation"""
    
    def __init__(self, config):
        self.config = config
        self.blocked_commands = config.get("security", {}).get("blocked_commands", [])
        self.allowed_services = config.get("direct_actions", {}).get("allowed_services", [])
    
    async def validate_llm_output(self, llm_output: Dict, context: Dict) -> Dict:
        """Validate LLM output against security policies"""
        validation_result = {
            "safe": False,
            "risks": [],
            "approved_actions": [],
            "blocked_actions": []
        }
        
        # 1. Check for structured output compliance
        if not self._validate_json_schema(llm_output):
            validation_result["risks"].append("Invalid JSON schema structure")
            return validation_result
        
        # 2. Command safety validation
        if "command_list" in llm_output:
            command_validation = await self._validate_commands(llm_output["command_list"])
            validation_result["approved_actions"] = command_validation["approved"]
            validation_result["blocked_actions"] = command_validation["blocked"]
        
        # 3. Code fix safety validation
        if "proposed_fix_diff" in llm_output:
            code_validation = await self._validate_code_fix(llm_output)
            if not code_validation["safe"]:
                validation_result["risks"].extend(code_validation["risks"])
        
        validation_result["safe"] = len(validation_result["risks"]) == 0
        return validation_result
    
    def _validate_json_schema(self, output: Dict) -> bool:
        """Validate mandatory LLM output schema"""
        required_fields = ["vulnerability_id", "cve_data", "proposed_fix_diff", "fix_safety_rating"]
        return all(field in output for field in required_fields)
    
    async def _validate_commands(self, commands: List[str]) -> Dict:
        """Validate system commands against security policies"""
        approved = []
        blocked = []
        
        for cmd in commands:
            if self._is_command_safe(cmd):
                approved.append(cmd)
            else:
                blocked.append(cmd)
        
        return {"approved": approved, "blocked": blocked}
    
    def _is_command_safe(self, command: str) -> bool:
        """Check if a command is safe to execute"""
        # Absolute prohibition of shell=True equivalent patterns
        if any(unsafe in command for unsafe in [";", "|", "&&", "||", "$(", "`"]):
            return False
        
        # Check against blocked commands
        if any(blocked in command.lower() for blocked in self.blocked_commands):
            return False
        
        # Service management safety
        if any(service_cmd in command for service_cmd in ["systemctl", "service"]):
            service_name = self._extract_service_name(command)
            return service_name in self.allowed_services
        
        return True
    
    def _extract_service_name(self, command: str) -> str:
        """Extract service name from systemctl commands"""
        try:
            parts = shlex.split(command)
            if "systemctl" in parts and len(parts) > 2:
                return parts[2]  # systemctl [action] [service]
        except:
            pass
        return ""
    
    async def _validate_code_fix(self, output: Dict) -> Dict:
        """Validate code fixes for security issues"""
        risks = []
        fix_diff = output.get("proposed_fix_diff", "")
        
        # Check for SQL injection vulnerabilities
        if "execute(" in fix_diff and ("%" in fix_diff or "format(" in fix_diff):
            risks.append("Potential SQL injection in proposed fix")
        
        # Check for command injection
        if "subprocess" in fix_diff and "shell=True" in fix_diff:
            risks.append("Command injection vulnerability with shell=True")
        
        # Check for path traversal
        if "open(" in fix_diff and "user_input" in fix_diff:
            risks.append("Potential path traversal vulnerability")
        
        return {"safe": len(risks) == 0, "risks": risks}
