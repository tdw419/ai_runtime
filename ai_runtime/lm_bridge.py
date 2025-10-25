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
from .code_validator import CodeValidator
from .git_manager import GitManager
from .test_generator import TestGenerator


RUNTIME_SYSTEM_PROMPT = """You are an AI development agent operating in a RUNTIME ENVIRONMENT.

You do NOT respond with chat or explanations. You respond ONLY with JSON directives.

Available actions:
- "create_file": {"filepath": "path/to/file.py", "content": "file contents"}
- "read_file": {"filepath": "path/to/file.py"}
- "modify_file": {"filepath": "path/to/file.py", "new_content": "updated contents"}
- "add_import_ast": {"filepath": "path/to/file.py", "module_name": "os", "alias": "os_alias"}
- "add_function_ast": {"filepath": "path/to/file.py", "function_code": "def my_func(): pass"}
- "delete_file": {"filepath": "path/to/file.py"}
- "run_python": {"command": "print('hello')"}
- "run_shell": {"command": "pip install flask"}
- "project_tree": {}

IMPORTANT RULES:
1. Before modifying a file, ALWAYS read_file first to see current contents
2. Check module status - DO NOT edit frozen modules
3. Keep changes surgical and focused
4. After creating/modifying code, test it with run_python or run_shell. Expect validation feedback.
5. Work in small, testable steps. Your code will be validated for correctness.
6. You will receive execution results and validation feedback after each step. If there are errors, you are expected to fix them.

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

ACCEPTANCE CRITERIA: {acceptance_criteria}
"""


class LMStudioRuntimeSession:
    """Manages an interactive session with LM Studio and the runtime"""

    def __init__(self, model_name: str, lm_base_url: str, project_root: str, session_id: Optional[str] = None):
        self.model_name = model_name
        self.lm_base_url = lm_base_url
        self.project_root = Path(project_root).resolve()

        # Session Management
        self.session_dir = self.project_root / ".ai_sessions"
        self.session_dir.mkdir(exist_ok=True)
        self.history = []

        if session_id:
            self.load_session(session_id)
        else:
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize memory system
        self.memory = RuntimeMemory(project_root)

        # Initialize sandbox runtime
        self.runtime = SandboxRuntime(str(self.project_root), self.memory, self.session_id)

        # Initialize code validator
        self.validator = CodeValidator(self.project_root)

        # Initialize Git Manager and Test Generator
        self.git_manager = GitManager(str(self.project_root))
        self.test_generator = TestGenerator(str(self.project_root))

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
                return f'{{"error": "Status {response.status_code}"}}'

        except Exception as e:
            return f'{{"error": "Error calling LM Studio: {str(e)}"}}'

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
        """Process initial mission intake, generate a plan, and create steps."""
        print("\n🎯 Mission Intake & Planning...")

        lines = user_request.split('\n')
        title = lines[0].replace("New mission: ", "").strip() if len(lines) > 0 else "Untitled Mission"
        detail = lines[1].replace("Details: ", "").strip() if len(lines) > 1 else title
        acceptance_criteria = lines[2].replace("Acceptance Criteria: ", "").strip() if len(lines) > 2 else "No acceptance criteria provided."

        planning_prompt = f"""
        Based on the following mission, decompose it into a series of smaller, verifiable sub-steps.
        Do not generate code. Only generate the plan.

        MISSION: {title}
        DETAILS: {detail}
        ACCEPTANCE CRITERIA: {acceptance_criteria}

        Respond with JSON only, in the format:
        {{
          "plan": [
            {{"title": "Sub-step 1", "detail": "Description of sub-step 1"}},
            {{"title": "Sub-step 2", "detail": "Description of sub-step 2"}}
          ]
        }}
        """

        response = self._call_lm_studio(planning_prompt)
        plan_data = self._parse_ai_response(response)

        if not plan_data or "plan" not in plan_data:
            # Fallback to a single step if planning fails
            module = self.memory.get_or_create_module("main", "./", title, "active")
            step = self.memory.create_step(module["id"], title, detail, acceptance_criteria)
            print("✅ Planning failed. Created a single step for the mission.")
            return {"module": module, "steps": [step]}

        module = self.memory.get_or_create_module("main", "./", title, "active")
        steps = []
        for sub_step in plan_data["plan"]:
            step = self.memory.create_step(module["id"], sub_step["title"], sub_step["detail"], acceptance_criteria)
            steps.append(step)

        print(f"✅ AI generated a plan with {len(steps)} steps.")
        return {"module": module, "steps": steps}

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
        """Execute one development step with Git transactions and auto-testing."""

        # 1. Get the next pending step or create one
        if not self.current_step_id:
            next_step = self.memory.get_next_step()
            if not next_step:
                intake_result = self.intake_mission(user_request)
                if not intake_result.get("steps"):
                    return {"success": False, "error": "Mission intake failed to produce steps."}
                self.current_step_id = intake_result["steps"][0]["id"]
            else:
                self.current_step_id = next_step["id"]

        self.memory.update_step_status(self.current_step_id, "in_progress")
        step_details = self.memory.get_step_details(self.current_step_id)

        # 2. Start a new Git branch for this step
        self.git_manager.begin_step(self.current_step_id, step_details["title"])

        # 3. Build prompt and call AI
        context = self.memory.get_context_summary()
        acceptance_criteria = step_details.get("acceptance_criteria", "Not specified")
        prompt = RUNTIME_SYSTEM_PROMPT.format(
            context=context,
            user_request=user_request,
            acceptance_criteria=acceptance_criteria
        )
        response = self._call_lm_studio(prompt)
        ai_plan = self._parse_ai_response(response)

        if not ai_plan:
            self.git_manager.complete_step(self.current_step_id, success=False) # Rollback
            return {"success": False, "error": "Failed to parse AI response", "raw": response}

        # 4. Execute directives
        exec_results = []
        files_modified = []
        for directive in ai_plan.get("directives", []):
            result = self.runtime.execute_directive(directive, self.current_step_id)
            exec_results.append({"directive": directive, "result": result})
            if result.get("success") and directive.get("action") in ["create_file", "modify_file"]:
                files_modified.append(directive["parameters"]["filepath"])

        # 5. Auto-generate tests
        for filepath in files_modified:
            if self.test_generator.should_generate_tests(filepath, "create_file"):
                code = self.runtime.read_file(filepath).get("content", "")
                analysis = self.test_generator.analyze_code_for_testing(filepath, code)
                if analysis.get("needs_tests"):
                    test_code = self.test_generator.generate_test_file(analysis)
                    test_path = f"tests/test_{Path(filepath).name}"
                    test_gen_result = self.runtime.create_file(test_path, test_code, self.current_step_id)
                    exec_results.append({
                        "directive": {"action": "auto_generate_tests", "parameters": {"for": filepath}},
                        "result": test_gen_result
                    })

        # 6. Validation (Critique Turn)
        all_successful = all(r["result"].get("success", False) for r in exec_results)
        validation_errors = []
        if all_successful:
            lint_result = self.validator.run_lint(".")
            if not lint_result["success"]:
                validation_errors.append(f"Linting failed: {lint_result['errors']}")

            test_result = self.validator.run_tests("tests/")
            if not test_result["success"]:
                validation_errors.append(f"Tests failed: {test_result.get('stderr')}")

        # 7. Complete or Rollback Step
        if all_successful and not validation_errors:
            self.memory.update_step_status(self.current_step_id, "done")
            self.git_manager.complete_step(self.current_step_id, success=True)
            self.current_step_id = None # Move to next step in next iteration
        else:
            self.git_manager.complete_step(self.current_step_id, success=False)
            error_message = "Execution or validation failed. Rolling back changes."
            if validation_errors:
                error_message += "\nValidation Errors:\n" + "\n".join(validation_errors)
            # In a more advanced version, we would feed this back to the AI. For now, we just roll back.
            self.memory.update_step_status(self.current_step_id, "blocked")
            return {"success": False, "error": error_message, "execution_results": exec_results}

        self.save_session()
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
        self.runtime.close()
        self.memory.close()
