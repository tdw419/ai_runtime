# runtime_core.py
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any, List

from model_client import ModelClient
from sandbox import Sandbox
from code_guard import CodeGuard

APPROVED_DIR = "approved_modules"

STRUCTURED_PROMPT = """
You are an autonomous runtime engineer improving yourself.

CURRENT GOAL:
{goal}

SANDBOX FILES:
{project_tree}

LAST RESULT:
{last_result}

Respond ONLY with valid JSON:
- { "done": false, "actions": [ ... ], "message": "..." }
- OR { "done": true, "message": "..." }

Actions:
- "write_python_file": { "action": "write_python_file", "filepath": "<path>", "full_contents": "<ENTIRE PY FILE>" }
- "run_python_file": { "action": "run_python_file", "filepath": "<path>" }
- "propose_promotion": { "action": "propose_promotion", "from_filepath": "<sandbox path>", "approved_name": "<name in approved_modules>" }

Rules:
- No commentary outside JSON.
- Always provide full file contents for writes.
- Code MUST be valid Python syntax.
- Propose promotion for stable, tested modules.
"""

class SelfImprovingRuntime:
    def __init__(self, workspace_root: str, model_endpoint: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.sandbox = Sandbox(workspace_root)
        self.guard = CodeGuard(workspace_root)
        self.model = ModelClient(endpoint=model_endpoint)
        self.goal = "Improve the AI runtime's ability to manage itself safely and efficiently."
        self.last_result = "INIT"
        self.state_file = self.workspace_root / "runtime_state.json"
        self._load_state()

    def _load_state(self):
        """Load persistent state from JSON file."""
        if self.state_file.exists():
            with self.state_file.open("r") as f:
                state = json.load(f)
                self.goal = state.get("goal", self.goal)
                self.last_result = state.get("last_result", "INIT")
        else:
            self._save_state()

    def _save_state(self):
        """Save current state to JSON file."""
        state = {"goal": self.goal, "last_result": self.last_result}
        with self.state_file.open("w") as f:
            json.dump(state, f, indent=2)

    def _summarize_tree(self) -> str:
        tree = self.sandbox.list_tree()
        return "\n".join(tree["files"]) if tree["success"] else "ERROR listing files"

    def _build_prompt(self) -> str:
        return STRUCTURED_PROMPT.format(
            goal=self.goal,
            project_tree=self._summarize_tree(),
            last_result=self.last_result
        )

    def _call_model_for_plan(self) -> Dict[str, Any]:
        prompt = self._build_prompt()
        raw = self.model.generate(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "done": False,
                "actions": [],
                "error": "MODEL_RETURNED_NON_JSON",
                "raw": raw
            }

    def _execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for action in actions:
            kind = action.get("action")
            if kind == "write_python_file":
                res = self.guard.safe_write_python(action.get("filepath"), action.get("full_contents", ""))
                results.append({"action": kind, "filepath": action.get("filepath"), "result": res})
            elif kind == "run_python_file":
                res = self.sandbox.run_python_file(action.get("filepath"))
                results.append({"action": kind, "filepath": action.get("filepath"), "result": res})
            elif kind == "propose_promotion":
                res = self._propose_promotion(action.get("from_filepath"), action.get("approved_name"))
                results.append({"action": kind, "from": action.get("from_filepath"), "to": action.get("approved_name"), "result": res})
            else:
                results.append({"action": kind, "error": "UNKNOWN_ACTION_TYPE"})
        return results

    def _propose_promotion(self, sandbox_rel_path: str, approved_filename: str) -> Dict[str, Any]:
        try:
            src_abs = self.sandbox._safe(sandbox_rel_path)
            approved_root = Path(APPROVED_DIR).resolve()
            approved_root.mkdir(exist_ok=True)
            text = src_abs.read_text()
            if sandbox_rel_path.endswith(".py") and not self.guard.is_valid_python(text):
                return {"success": False, "error": "Not valid Python, not promoting"}
            dst_abs = approved_root / approved_filename
            shutil.copyfile(src_abs, dst_abs)
            return {"success": True, "approved_path": str(dst_abs)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def tick(self) -> Dict[str, Any]:
        plan = self._call_model_for_plan()
        if plan.get("done", False):
            self.last_result = plan.get("message", "Goal complete.")
            self._save_state()
            return {"state": "DONE", "message": self.last_result}
        actions = plan.get("actions", [])
        if not actions:
            self.last_result = plan.get("error", "NO_ACTIONS")
            self._save_state()
            return {"state": "NO_ACTIONS", "last_result": self.last_result, "raw": plan.get("raw", "")}
        results = self._execute_actions(actions)
        self.last_result = json.dumps(results, indent=2)[:800]
        self._save_state()
        return {"state": "ACTIONS_EXECUTED", "results": results}
