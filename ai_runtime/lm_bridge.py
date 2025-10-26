"""
LM Studio Bridge - Connects local AI models to the runtime environment
"""
import json
import requests
from typing import Dict, Any, Optional
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

    def __init__(self, model_name: str, lm_base_url: str, project_root: str):
        self.model_name = model_name
        self.lm_base_url = lm_base_url
        self.project_root = project_root

        # Initialize memory system
        memory_db = f"{project_root}/runtime_state.db"
        self.memory = RuntimeMemory(memory_db)

        # Initialize sandbox runtime
        self.runtime = SandboxRuntime(project_root, self.memory)

        # Current step being worked on
        self.current_step_id = None

        # Token Management
        self.MODEL_CONTEXT_WINDOW = 4096
        self.RESPONSE_SAFETY_MARGIN = 1024

    def _count_tokens(self, text: str) -> int:
        """A simple approximation for token counting."""
        return len(text) // 4

    def _trim_context(self, context: str, max_tokens: int) -> str:
        """Trims the context string to fit within the token budget."""
        if self._count_tokens(context) <= max_tokens:
            return context

        # Simple truncation for now, can be made smarter later
        trimmed_len = int(max_tokens * 3.5) # Estimate character length
        return context[:trimmed_len] + "\n... (context truncated)"

    def _call_lm_studio(self, prompt: str) -> str:
        """Call LM Studio API"""
        try:
            response = requests.post(
                f"{self.lm_base_url}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "You are a code execution agent. Respond only with JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
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

    def _parse_ai_response(self, response: str, original_prompt: str = "") -> Optional[Dict[str, Any]]:
        """Parse AI response as JSON, with a retry mechanism for fixing malformed JSON."""
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
            print("⚠️ Malformed JSON detected. Attempting to repair...")
            repair_prompt = f"""The following response is not valid JSON. Please fix the syntax and return ONLY the corrected, valid JSON.

Malformed Response:
{response}
"""
            repaired_response = self._call_lm_studio(repair_prompt)
            try:
                # Try parsing the repaired response
                return json.loads(repaired_response)
            except json.JSONDecodeError:
                print("❌ JSON repair failed.")
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
        parsed = self._parse_ai_response(response, original_prompt=intake_prompt)

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

    def step(self, user_request: str) -> Dict[str, Any]:
        """Execute one development step"""

        # Get or create step for this request
        if not self.current_step_id:
            intake_result = self.intake_mission(user_request)
            self.current_step_id = intake_result["step"]["id"]
            self.memory.update_step_status(self.current_step_id, "in_progress")

        # Get current project context
        context = self.memory.get_context_summary()

        # Build the prompt skeleton to calculate available context size
        prompt_skeleton = RUNTIME_SYSTEM_PROMPT.format(context="{context}", user_request=user_request)
        prompt_skeleton_tokens = self._count_tokens(prompt_skeleton)

        # Calculate the token budget for the context
        context_token_budget = self.MODEL_CONTEXT_WINDOW - prompt_skeleton_tokens - self.RESPONSE_SAFETY_MARGIN

        # Trim the context to fit the budget
        trimmed_context = self._trim_context(context, context_token_budget)

        # Build the final prompt
        prompt = RUNTIME_SYSTEM_PROMPT.format(
            context=trimmed_context,
            user_request=user_request
        )

        # Call LM Studio
        response = self._call_lm_studio(prompt)

        # Parse response
        ai_plan = self._parse_ai_response(response, original_prompt=prompt)

        if not ai_plan:
            return {
                "success": False,
                "error": "Failed to parse AI response as JSON",
                "raw": response
            }

        # Execute directives
        exec_results = []
        for directive in ai_plan.get("directives", []):
            result = self.runtime.execute_directive(directive, self.current_step_id)
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
