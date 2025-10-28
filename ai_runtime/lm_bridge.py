"""
LM Studio Bridge - Connects local AI models to the runtime environment
"""
import json
import requests
from typing import Dict, Any, Optional
from .memory import RuntimeMemory
from .sandbox_runtime import RuntimeSandbox
from .code_guard import CodeGuard


class SafeDict(dict):
    """A dictionary that returns '{key}' for missing keys during string formatting."""
    def __missing__(self, key):
        return "{" + key + "}"


CHAT_PROMPT = """
You are an AI assistant helping to manage a runtime environment. Respond in natural language to the user's query: {user_input}.
Summarize the current state, explain any concerns, and suggest next actions. Do not propose file edits or output JSON.
"""

STRUCTURED_PROMPT = """
You are a code execution agent. Respond ONLY with valid JSON describing the actions to take for: {user_input}.
Use this schema: { "action": "edit_file", "filepath": "...", "full_new_contents": "..." } or similar.
Do not include explanations or non-JSON content.
"""

CHAT_PLAN_PROMPT = """
You are an AI assistant managing a runtime environment. For the query: {user_input}, provide:
1. A brief explanation in natural language summarizing your plan.
2. A JSON block of intended actions, separated by ```json
...
```.
Example:
Operator-facing summary: I'm adding caching to improve performance.
```json
[{ "action": "edit_file", "filepath": "...", "full_new_contents": "..." }]
```
"""

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
        self.runtime = RuntimeSandbox(project_root)
        self.code_guard = CodeGuard(project_root)
        
        # Current step being worked on
        self.current_step_id = None
        self.task_queue = []

    def _build_prompt_chat(self, user_input: str) -> str:
        return CHAT_PROMPT.format(user_input=user_input)

    def _build_prompt_structured(self, user_input: str) -> str:
        return STRUCTURED_PROMPT.format(user_input=user_input)

    def _build_prompt_chatplan(self, user_input: str) -> str:
        return CHAT_PLAN_PROMPT.format(user_input=user_input)

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
        
        # Create initial steps
        for step_title in parsed.get("initial_steps", [user_request]):
            step = self.memory.create_step(
                module["id"],
                step_title,
                user_request
            )
            self.task_queue.append(step)

        print(f"✅ Created module '{module['name']}' and initial steps.")
        return {"module": module, "steps": self.task_queue}

    def step(self, user_request: str, mode: str) -> Dict[str, Any]:
        """Execute one development step"""
        
        if not self.task_queue:
            self.intake_mission(user_request)

        # Process tasks until the queue is empty or requires input
        while self.task_queue:
            current_task = self.task_queue.pop(0)
            self.current_step_id = current_task['id']
            self.memory.update_step_status(self.current_step_id, "in_progress")

            # Get current project context
            context = self.memory.get_context_summary()

            # Build prompt with context
            if mode == "structured":
                prompt = self._build_prompt_structured(user_request)
            elif mode == "chat+plan":
                prompt = self._build_prompt_chatplan(user_request)
            else: # default to structured
                prompt_vars = SafeDict(
                    context=context,
                    user_request=f"Current task: {current_task['title']}\n\nOverall goal: {user_request}"
                )
                prompt = RUNTIME_SYSTEM_PROMPT.format_map(prompt_vars)

            # Call LM Studio
            response = self._call_lm_studio(prompt)

            # Parse response
            ai_plan = self._parse_ai_response(response)

            if not ai_plan:
                # Put task back in queue and report error
                self.task_queue.insert(0, current_task)
                return {
                    "success": False,
                    "error": "Failed to parse AI response as JSON",
                    "raw": response
                }

            # Execute directives
            exec_results = []
            all_successful = True
            for directive in ai_plan.get("directives", []):
                action = directive.get("action")
                parameters = directive.get("parameters", {})
                result = {}

                if action == "edit_file":
                    result = self.code_guard.apply_edit(
                        parameters.get("filepath"),
                        parameters.get("full_new_contents")
                    )
                elif action == "run_python_file":
                    result = self.runtime.run_python_file(parameters.get("filepath"))
                # Add other actions here
                else:
                    result = {"success": False, "error": f"Unknown action: {action}"}

                exec_results.append({
                    "directive": directive,
                    "result": result
                })
                if not result.get("success"):
                    all_successful = False

            if all_successful:
                self.memory.update_step_status(self.current_step_id, "done")
            else:
                self.memory.update_step_status(self.current_step_id, "blocked")
                # Stop processing if a step fails
                break

        return {
            "success": True,
            "ai_reasoning": "Completed a sequence of autonomous steps.",
            "next_steps": "Ready for next user input, or continuing with remaining tasks.",
            "execution_results": [], # This would need to be aggregated if we want to show all results
            "project_tree": self.runtime.project_tree(),
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
