#!/usr/bin/env python3
"""
AI Runtime Launcher - Start an interactive AI development session with persistent memory
"""
import os
import sys
import requests
import subprocess
from pathlib import Path
from ai_runtime.lm_bridge import LMStudioRuntimeSession
from ai_runtime.project_templates import apply_template, PROJECT_TEMPLATES
from ai_runtime.code_validator import CodeValidator

LM_STUDIO_URL = "http://localhost:1234"


def list_models() -> list:
    """Get available models from LM Studio"""
    try:
        resp = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
        data = resp.json()
        return [m["id"] for m in data.get("data", [])]
    except Exception as e:
        print(f"⚠️  Could not list models: {e}")
        print("Make sure LM Studio is running on http://localhost:1234")
        return []


def pick_model(models: list) -> str:
    """Let user select a model"""
    if not models:
        raise RuntimeError("No models available. Load a model in LM Studio first.")

    if len(models) == 1:
        print(f"🧠 Using only available model: {models[0]}")
        return models[0]

    print("\n📋 Available models:")
    for idx, model in enumerate(models):
        print(f"  [{idx}] {model}")
    
    while True:
        try:
            choice = input("\nSelect model number: ").strip()
            if choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(models):
                    return models[idx]
            print("Invalid selection. Try again.")
        except KeyboardInterrupt:
            print("\n👋 Cancelled")
            sys.exit(0)


def print_tree(tree: dict, indent: int = 0):
    """Print project tree in readable format"""
    for key in sorted(tree.keys()):
        if key.endswith('/'):
            print("  " * indent + f"📁 {key}")
        else:
            print("  " * indent + f"📄 {key}")


def pick_template() -> str:
    """Let user select a project template"""
    print("\n🚀 Project Templates:")
    templates = list(PROJECT_TEMPLATES.keys())
    for idx, name in enumerate(templates):
        description = PROJECT_TEMPLATES[name]['description']
        print(f"  [{idx}] {name} - {description}")

    print(f"  [{len(templates)}] None - Start with an empty project")

    while True:
        try:
            choice = input("\nSelect a template to start with: ").strip()
            if choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(templates):
                    return templates[idx]
                elif idx == len(templates):
                    return None
            print("Invalid selection. Try again.")
        except KeyboardInterrupt:
            print("\n👋 Cancelled")
            sys.exit(0)


def pick_session(project_root: Path) -> str:
    """Let user select a previous session to resume"""
    session_dir = project_root / ".ai_sessions"
    if not session_dir.exists():
        return None

    sessions = sorted([f.stem for f in session_dir.glob("*.json")], reverse=True)
    if not sessions:
        return None

    print("\n🔄 Available Sessions to Resume:")
    for idx, name in enumerate(sessions):
        print(f"  [{idx}] {name}")

    print(f"  [{len(sessions)}] None - Start a new session")

    while True:
        try:
            choice = input("\nSelect a session to resume: ").strip()
            if choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(sessions):
                    return sessions[idx]
                elif idx == len(sessions):
                    return None
            print("Invalid selection. Try again.")
        except KeyboardInterrupt:
            print("\n👋 Cancelled")
            sys.exit(0)


def main():
    print("=" * 60)
    print("   🤖 AI RUNTIME LAUNCHER")
    print("   Persistent Memory + Local Model + Sandboxed Builder")
    print("=" * 60)

    # Check LM Studio connection
    print("\n🔍 Connecting to LM Studio...")
    models = list_models()
    
    if not models:
        print("\n❌ No models found. Please:")
        print("   1. Start LM Studio")
        print("   2. Load a model (e.g., Qwen, Llama, Mistral)")
        print("   3. Start the local server (usually port 1234)")
        print("   4. Run this script again")
        return

    # Select model
    model_name = pick_model(models)

    # Setup project directory
    project_root_path = Path(os.path.abspath("./ai_runtime_project"))
    project_root = str(project_root_path)
    os.makedirs(project_root, exist_ok=True)
    print(f"\n📂 Project workspace: {project_root}")
    print(f"💾 Database: {project_root}/runtime_state.db")

    # Initialize Git repository
    if not (project_root_path / ".git").exists():
        print("Initializing Git repository...")
        subprocess.run(["git", "init"], cwd=project_root, capture_output=True)

    # Pick session to resume or start new
    session_id = pick_session(project_root_path)

    # Initialize runtime session
    print("\n⚙️  Initializing runtime...")
    session = LMStudioRuntimeSession(
        model_name=model_name,
        lm_base_url=LM_STUDIO_URL,
        project_root=project_root,
        session_id=session_id
    )

    # Apply project template if it's a new session
    if not session_id:
        template_name = pick_template()
        if template_name:
            print(f"\nApplying template '{template_name}'...")
            result = apply_template(template_name, project_root_path)

            if result.get("post_commands"):
                print("\nRunning post-template commands...")
                for command in result["post_commands"]:
                    print(f"$ {command}")
                    exec_result = session.runtime.run_shell(command)
                    if not exec_result["success"]:
                        print(f"  ⚠️  Command failed: {exec_result.get('stderr') or exec_result.get('error')}")

            if result.get("notes"):
                general_module = session.memory.get_or_create_module(
                    name="general",
                    path="./",
                    description="General project notes and context"
                )
                for note in result["notes"]:
                    session.memory.add_note(general_module["id"], f"[Template: {template_name}] {note}")
                print("📝 Template notes added to memory.")

    print(f"\n🎯 Runtime session '{session.session_id}' is LIVE!")
    print("\n" + "=" * 60)
    print("💡 TIPS:")
    print("   • The AI will create modules and track progress in the database")
    print("   • Modules can be frozen to protect working code")
    print("   • All actions are logged for review")
    print("\n📝 Try commands like:")
    print("   • 'Create a Flask web server with user authentication'")
    print("   • 'Build a todo list application with SQLite'")
    print("   • 'Add API endpoints for user management'")
    print("\n🔧 Special commands:")
    print("   • 'status'  - Show current modules, steps, and recent actions")
    print("   • 'tree'    - Show project file structure")
    print("   • 'freeze <module_name>' - Freeze a module to prevent edits")
    print("   • 'unfreeze <module_name>' - Unfreeze a module")
    print("   • 'modules' - List all modules and their status")
    print("   • 'template' - Show available project templates")
    print("   • 'sessions' - List and resume previous sessions")
    print("   • 'mission' - Start a new mission intake")
    print("   • 'explain' - Explain the AI's current task and goal")
    print("   • 'validate' - Run validation suite on the project")
    print("   • 'exit'    - Quit the runtime")
    print("=" * 60)

    # Interactive loop
    while True:
        try:
            user_input = input("\n💬 you> ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 Shutting down AI Runtime...")
                session.close()
                break
                
            elif user_input.lower() == "status":
                status = session.get_status()
                print("\n📊 RUNTIME STATUS")
                print("=" * 60)
                
                print("\n🗂️  MODULES:")
                for mod in status["modules"]:
                    status_icon = {
                        'frozen': '❄️',
                        'active': '✅',
                        'staging': '🚧'
                    }.get(mod['status'], '❓')
                    print(f"  {status_icon} {mod['name']} (priority {mod['priority']})")
                    print(f"     Path: {mod['path']}")
                    print(f"     {mod['description']}")
                
                print("\n📋 ACTIVE STEPS:")
                if status["active_steps"]:
                    for step in status["active_steps"]:
                        print(f"  • [{step['status']}] {step['title']}")
                        print(f"    Module: {step['module_name']}")
                else:
                    print("  (no active steps)")
                
                print("\n🔄 RECENT ACTIONS:")
                for action in status["recent_actions"][:5]:
                    success_icon = '✅' if action['success'] else '❌'
                    print(f"  {success_icon} {action['action_type']}")
                
                continue
                
            elif user_input.lower() == "tree":
                tree = session.runtime.project_tree()
                print("\n📁 PROJECT STRUCTURE:")
                print_tree(tree["tree"])
                continue
                
            elif user_input.lower().startswith("freeze "):
                module_name = user_input[7:].strip()
                session.freeze_module(module_name)
                continue
                
            elif user_input.lower().startswith("unfreeze "):
                module_name = user_input[9:].strip()
                session.unfreeze_module(module_name)
                continue
                
            elif user_input.lower() == "modules":
                modules = session.memory.list_modules()
                print("\n🗂️  ALL MODULES:")
                for mod in modules:
                    status_icon = {
                        'frozen': '🔒',
                        'active': '✅',
                        'staging': '🚧'
                    }.get(mod['status'], '❓')
                    print(f"  {status_icon} {mod['name']} - {mod['description']}")
                    print(f"     Status: {mod['status']} | Priority: {mod['priority']}")
                continue

            elif user_input.lower() == "template":
                pick_template() # Just show the templates
                continue

            elif user_input.lower() == "sessions":
                pick_session(project_root_path) # Just show the sessions
                continue

            elif user_input.lower() == 'mission':
                title = input("Step Title: ").strip()
                detail = input("Step Detail: ").strip()
                acceptance_criteria = input("Acceptance Criteria: ").strip()
                user_input = f"New mission: {title}\nDetails: {detail}\nAcceptance Criteria: {acceptance_criteria}"
                result = session.step(user_input)

            elif user_input.lower() == 'explain':
                status = session.get_status()
                if not status["active_steps"]:
                    print("\n🧠 No active mission. Use the 'mission' command to start one.")
                    continue

                current_step = status["active_steps"][0]
                print(f"\n🧠 EXPLAINING CURRENT TASK")
                print("=" * 60)
                print(f"TASK: {current_step['title']}")
                print(f"GOAL: {session.memory.get_step_details(current_step['id']).get('acceptance_criteria')}")

                if status["recent_actions"]:
                    last_action = status["recent_actions"][0]
                    success_icon = '✅' if last_action['success'] else '❌'
                    print(f"LAST ACTION: {success_icon} {last_action['action_type']}")
                else:
                    print("LAST ACTION: No actions taken yet for this step.")

            elif user_input.lower() == "validate":
                print("\n🔬 Running validation suite...")
                validator = CodeValidator(project_root)

                # Find all Python files, excluding dotfiles/dirs
                py_files = []
                for root, _, files in os.walk(project_root):
                    # Skip dot directories
                    if any(part.startswith('.') for part in Path(root).relative_to(project_root_path).parts):
                        continue
                    for file in files:
                        if file.endswith(".py"):
                            py_files.append(os.path.relpath(os.path.join(root, file), project_root))

                errors = []
                print(f"Found {len(py_files)} Python files to check.")

                for file_path in py_files:
                    print(f"  - Linting {file_path}...")
                    lint_result = validator.run_lint(file_path)
                    if not lint_result["success"]:
                        errors.append(f"Linting Error in {file_path}:\n{lint_result['errors']}\n")

                test_dir = project_root_path / "tests"
                if test_dir.exists() and test_dir.is_dir():
                    print("  - Running tests...")
                    test_result = validator.run_tests("tests/")
                    if not test_result["success"]:
                        errors.append(f"Test Failures:\n{test_result.get('stderr') or test_result.get('stdout')}\n")
                else:
                    print("  - No 'tests' directory found, skipping tests.")

                if errors:
                    print("\n❌ Validation Failed:")
                    for error in errors:
                        print(error)
                else:
                    print("\n✅ All validation checks passed!")
                continue

            else:
                # Process AI directive
                print("🔄 Processing...")
                result = session.step(user_input)

            if not result.get("success"):
                print(f"\n❌ Step failed: {result.get('error')}")
                if "raw" in result:
                    print(f"\nRaw AI output:\n{result['raw'][:300]}...")
                continue

            # Display results
            print(f"\n🤖 AI Reasoning: {result['ai_reasoning']}")
            print(f"🔜 Next Steps: {result['next_steps']}")

            # Show execution details
            print(f"\n📊 Execution Results ({len(result['execution_results'])} actions):")
            for i, exec_item in enumerate(result["execution_results"], 1):
                directive = exec_item["directive"]
                action = directive.get("action")
                r = exec_item["result"]
                
                status = "✅" if r.get("success") else "❌"
                print(f"\n  {i}. {action} {status}")
                
                if "filepath" in r:
                    print(f"     File: {r['filepath']}")
                if "message" in r:
                    print(f"     {r['message']}")
                if "stdout" in r and r["stdout"].strip():
                    output = r["stdout"][:150].strip()
                    if output:
                        print(f"     Output: {output}...")
                if "stderr" in r and r["stderr"].strip():
                    error = r["stderr"][:150].strip()
                    print(f"     Error: {error}...")
                if "error" in r and r["error"]:
                    print(f"     Error: {r['error']}")

            # Show updated project structure
            print(f"\n📂 Updated Project:")
            print_tree(result["project_tree"])
            print("=" * 60)

        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            session.close()
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
