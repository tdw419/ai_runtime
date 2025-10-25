"""
LM Studio Bridge - Connects local AI models to the runtime environment
"""
import json
import requests
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from .memory import RuntimeMemory
from .sandbox import SandboxRuntime


RUNTIME_SYSTEM_PROMPT = """You are an AI development agent operating in a RUNTIME ENVIRONMENT.

You do NOT respond with chat or explanations. You respond ONLY with JSON directives.

Available actions:
- "create_file": {"filepath": "path/to/file.py", "content": "file contents"}
- "read_file": {"filepath": "path/to/file.py"}
- "modify_file": {"filepath": "path/to/file.py", "new_content": "updated contents"}
- "delete_file": {"filepath": "path/to/file.py"}
- "run_python": {"command": "print('hello')"}
- "run_shell": {"command": "pip install flask"}
- "project_tree": {}

IMPORTANT RULES:
1. Before modifying a file, ALWAYS read_file first to see current contents
2. Check module status - DO NOT edit frozen modules
3. Keep changes surgical and focused
4. After creating/modifying code, test it with run_python or run_shell
5. Work in small, testable steps
6. You will receive execution results after each step

Response format (JSON ONLY):
{
  "reasoning": "Brief explanation of what you're doing",
  "directives": [
    {
      "action": "create_file",
      "parameters": {"filepath": "app.py", "content": "..."}
    },
    {
      "action": "run_shell",
      "parameters": {"command": "pip install flask"}
    }
  ],
  "next_steps": "What should happen next"
}

PROJECT STATE CONTEXT:
{context}

USER REQUEST: {user_request}
"""


class LMStudioRuntimeSession:
    """Manages an interactive session with LM Studio and the runtime"""
    
    def __init__(self, model_name: str, lm_base_url: str, project_root: str, session_id: Optional[str] = None):
        self.model_name = model_name
        self.lm_base_url = lm_base_url
        self.project_root = Path(project_root)
        
        # Session Management
        self.session_dir = self.project_root / ".ai_sessions"
        self.session_dir.mkdir(exist_ok=True)
        self.history = []

        if session_id:
            self.load_session(session_id)
        else:
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize memory system
        memory_db = str(self.project_root / "runtime_state.db")
        self.memory = RuntimeMemory(memory_db)
        
        # Initialize sandbox runtime
        self.runtime = SandboxRuntime(str(self.project_root), self.memory)
        
        # Current step being worked on
        self.current_step_id = None

        # Read-before-write tracking
        self.recent_reads = set()

    def _call_lm_studio(self, prompt: str) -> str:
        """Call LM Studio API"""
        messages = [
            {"role": "system", "content": "You are a code execution agent. Respond only with JSON."},
            *self.history[-4:], # Include last 2 user/assistant turn pairs
            {"role": "user", "content": prompt}
        ]

        try:
            response = requests.post(
                f"{self.lm_base_url}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"}
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Error: Status {response.status_code}"
        
        except Exception as e:
            return f"Error calling LM Studio: {str(e)}"

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response as JSON"""
        try:
            # Try to extract JSON if wrapped in markdown
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            return json.loads(response)
        except json.JSONDecodeError:
            return None

    def intake_mission(self, user_request: str) -> Dict[str, Any]:
        """Process initial mission intake and create module/step"""
        print("\n🎯 Mission Intake...")
        
        # Ask AI to analyze the request and suggest module structure
        intake_prompt = f"""Analyze this development request and suggest a module structure:

REQUEST: {user_request}

Respond with JSON only:
{{
  "suggested_module": "module_name",
  "module_path": "path/in/project",
  "description": "what this module does",
  "initial_steps": ["step 1", "step 2", "step 3"]
}}
"""
        
        response = self._call_lm_studio(intake_prompt)
        parsed = self._parse_ai_response(response)
        
        if not parsed:
            # Fallback: create generic module
            module = self.memory.get_or_create_module(
                name="main",
                path="./",
                description=user_request,
                default_status="active"
            )
            step = self.memory.create_step(module["id"], "Main Task", user_request)
            return {"module": module, "step": step}
        
        # Create module from AI suggestion
        module = self.memory.get_or_create_module(
            name=parsed["suggested_module"],
            path=parsed["module_path"],
            description=parsed["description"],
            default_status="active"
        )
        
        # Create initial step
        step = self.memory.create_step(
            module["id"],
            "Initial Implementation",
            user_request
        )
        
        print(f"✅ Created module '{module['name']}' and initial step")
        return {"module": module, "step": step}

    def save_session(self):
        """Save the current session state to a JSON file."""
        data = {
            "session_id": self.session_id,
            "model_name": self.model_name,
            "project_root": str(self.project_root),
            "history": self.history,
            "timestamp": datetime.now().isoformat()
        }
        path = self.session_dir / f"{self.session_id}.json"
        path.write_text(json.dumps(data, indent=2))

    def load_session(self, session_id: str):
        """Load a session state from a JSON file."""
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            print(f"⚠️  Session file not found: {path}")
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}" # Create new
            return

        print(f"🔄 Resuming session: {session_id}")
        raw = json.loads(path.read_text())
        self.session_id = raw["session_id"]
        self.history = raw["history"]
        self.model_name = raw.get("model_name", self.model_name)
        # Note: project_root should match, but we don't enforce it here

    def step(self, user_request: str) -> Dict[str, Any]:
        """Execute one development step"""
        
        # Get or create step for this request
        if not self.current_step_id:
            intake_result = self.intake_mission(user_request)
            self.current_step_id = intake_result["step"]["id"]
            self.memory.update_step_status(self.current_step_id, "in_progress")
        
        # Get current project context
        context = self.memory.get_context_summary()
        
        # Build prompt with context
        prompt = RUNTIME_SYSTEM_PROMPT.format(
            context=context,
            user_request=user_request
        )
        
        # Call LM Studio
        response = self._call_lm_studio(prompt)
        
        # Parse response
        ai_plan = self._parse_ai_response(response)
        
        if not ai_plan:
            return {
                "success": False,
                "error": "Failed to parse AI response as JSON",
                "raw": response
            }
        
        # Execute directives
        exec_results = []
        for directive in ai_plan.get("directives", []):
            action = directive.get("action")
            params = directive.get("parameters", {})

            if action == "modify_file":
                filepath = params.get("filepath")
                if filepath not in self.recent_reads:
                    result = {
                        "success": False,
                        "error": f"Safety violation: You must read '{filepath}' before modifying it.",
                        "safety_violation": True
                    }
                else:
                    result = self.runtime.execute_directive(directive, self.current_step_id)
            else:
                result = self.runtime.execute_directive(directive, self.current_step_id)

            if action == "read_file" and result.get("success"):
                self.recent_reads.add(params.get("filepath"))

            exec_results.append({
                "directive": directive,
                "result": result
            })
        
        # Check if step is complete
        all_successful = all(r["result"].get("success", False) for r in exec_results)
        if all_successful and "next_steps" in ai_plan:
            # Mark current step as done, clear current_step_id for next iteration
            self.memory.update_step_status(self.current_step_id, "done")
            self.current_step_id = None
        
        self.save_session() # Save session state after each step

        return {
            "success": True,
            "ai_reasoning": ai_plan.get("reasoning", ""),
            "next_steps": ai_plan.get("next_steps", ""),
            "execution_results": exec_results,
            "project_tree": self.runtime.project_tree()["tree"],
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current runtime status"""
        return {
            "modules": self.memory.list_modules(),
            "active_steps": self.memory.get_active_steps(),
            "recent_actions": self.memory.get_recent_actions(10),
            "project_tree": self.runtime.project_tree()
        }

    def freeze_module(self, module_name: str):
        """Freeze a module to protect it"""
        self.memory.freeze_module(module_name)
        print(f"🔒 Module '{module_name}' is now frozen")

    def unfreeze_module(self, module_name: str):
        """Unfreeze a module to allow edits"""
        self.memory.unfreeze_module(module_name)
        print(f"🔓 Module '{module_name}' is now unfrozen")

    def close(self):
        """Clean up resources"""
        self.memory.close()
