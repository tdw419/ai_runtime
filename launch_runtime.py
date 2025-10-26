#!/usr/bin/env python3
"""
AI Runtime Launcher - Start an interactive AI development session with persistent memory
"""
import os
import sys
import requests
import threading
from lm_bridge import LMStudioRuntimeSession
from system_stewardship_monitor import SystemStewardshipMonitor

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


def run_stewardship_monitor(monitor: SystemStewardshipMonitor):
    """
    The function that runs in a separate thread to perform system monitoring.
    """
    monitor.collect_system_baseline()

    check_interval_seconds = 120  # Check every 2 minutes
    while True:
        time.sleep(check_interval_seconds)
        anomalies = monitor.detect_anomalies()
        if anomalies:
            print(f"\n🚨 [STEWARDSHIP ALERT] {len(anomalies)} anomalies detected. Run 'status' for details.")
            # Auto-generate a report on detection
            report = monitor.generate_security_report()
            Path("SECURITY_REPORT.md").write_text(report)


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
    project_root = os.path.abspath("./ai_runtime_project")
    os.makedirs(project_root, exist_ok=True)
    print(f"\n📂 Project workspace: {project_root}")
    print(f"💾 Database: {project_root}/runtime_state.db")

    # Initialize runtime session
    print("\n⚙️  Initializing runtime...")
    session = LMStudioRuntimeSession(
        model_name=model_name,
        lm_base_url=LM_STUDIO_URL,
        project_root=project_root
    )

    print("\n🎯 Runtime session is LIVE!")
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
    print("   • 'exit'    - Quit the runtime")
    print("=" * 60)

    # Start the stewardship monitor in a background thread
    stewardship_monitor = SystemStewardshipMonitor()
    stewardship_thread = threading.Thread(
        target=run_stewardship_monitor, args=(stewardship_monitor,), daemon=True
    )
    stewardship_thread.start()
    print("🛡️  System Stewardship Monitor is running in the background.")
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
                        'frozen': '🔒',
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
                
                print("\n🛡️  SYSTEM STEWARDSHIP:")
                print(f"   • Security Events Logged: {len(stewardship_monitor.security_events)}")
                if stewardship_monitor.security_events:
                    print("     (See SECURITY_REPORT.md for details)")

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
