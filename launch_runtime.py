# launch_runtime.py
"""
AI Runtime Launcher - Phase 3.3 Complete Integration
Now with Collaboration & Escalation.
"""

import sys
import os
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("🚀 AI Runtime Steward - Starting Phase 3.3...")

    try:
        # Import all components
        from system_state_tracker import state_tracker
        from task_registry import TASK_REGISTRY
        from task_executor import TaskExecutor
        from task_scheduler import TaskScheduler
        from task_runner import TaskRunner
        from collaboration_manager import CollaborationManager # <-- NEW

        print("✅ All components loaded")

        # Initialize AI runtime components
        try:
            from ai_runtime.sandbox import SandboxRuntime
            from ai_runtime.memory import RuntimeMemory
            dummy_memory = RuntimeMemory(":memory:")
            sandbox = SandboxRuntime(".", memory=dummy_memory)
        except ImportError:
            sandbox = None

        class AIRuntime:
            def __init__(self, sandbox_instance):
                self.sandbox = sandbox_instance
            def execute_directive(self, directive: str):
                try:
                    if self.sandbox:
                        return self.sandbox.run_shell(f"echo 'Directive: {directive}'")
                    else:
                        return {"success": True, "stdout": f"Stub: {directive}"}
                except Exception as e:
                    return {"success": False, "error": str(e)}

        ai_runtime = AIRuntime(sandbox)

        # Initialize core components
        task_executor = TaskExecutor(ai_runtime, state_tracker)
        scheduler = TaskScheduler(state_tracker)
        task_runner = TaskRunner(task_executor)
        collaboration_manager = CollaborationManager() # <-- NEW

        # Inject collaboration manager into the executor (Phase 3.3)
        task_executor.collaboration_manager = collaboration_manager

        print("🤖 AI Runtime Steward Initialized")

        generate_status_report(state_tracker, TASK_REGISTRY, scheduler, collaboration_manager) # <-- NEW

        # Main interaction loop
        run_steward_loop(TASK_REGISTRY, task_executor, scheduler, task_runner, collaboration_manager) # <-- NEW

        print("👋 AI Runtime Steward shutdown complete")
        return 0
    
    except Exception as e:
        print(f"❌ Runtime error: {e}")
        return 1

def run_steward_loop(task_registry, task_executor, scheduler, task_runner, collaboration_manager): # <-- NEW
    """Main steward interaction loop with collaboration commands."""
    while True:
        try:
            print("\n" + "="*50)
            print("AI Runtime Steward - Phase 3.3")
            print("  'run_task <id>', 'list_tasks', 'status', 'exit'")
            print("  'view escalations', 'resolve_escalation <id> \"guidance\"'")

            user_input = input("\n steward> ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            elif user_input.lower() == 'list_tasks':
                list_available_tasks(task_registry)
            elif user_input.lower() == 'status':
                generate_status_report(state_tracker, task_registry, scheduler, collaboration_manager)
            elif user_input.startswith('run_task '):
                execute_task_command(user_input[9:].strip(), task_registry, task_executor)
            # --- NEW Collaboration Commands (Phase 3.3) ---
            elif user_input.startswith("view escalations"):
                pending = collaboration_manager.get_pending_escalations()
                if pending:
                    print("🚨 Pending escalations:")
                    for eid, esc in pending.items():
                        print(f"  - {eid}: {esc['task_id']} - {esc['step_description']}")
                else:
                    print("✅ No pending escalations.")
            elif user_input.startswith("resolve_escalation"):
                parts = user_input.split(" ", 2)
                if len(parts) >= 3:
                    esc_id, guidance = parts[1], parts[2].strip('"')
                    if collaboration_manager.resolve_escalation(esc_id, guidance):
                        print(f"✅ Escalation {esc_id} resolved.")
                    else:
                        print(f"❌ Escalation {esc_id} not found.")
                else:
                    print("Usage: resolve_escalation <id> \"guidance\"")
            else:
                # Natural language fallback
                nl_result = task_runner.run_from_text(user_input)
                if nl_result.get("success"):
                    print(f"🤖 Interpreted as: {nl_result['interpreted_task_name']}")
                else:
                    print(f"❌ {nl_result.get('error', 'Unknown command.')}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error in command loop: {e}")

# Note: A global state_tracker is assumed for simplicity.
from system_state_tracker import state_tracker

def generate_status_report(state_tracker, task_registry, scheduler, collaboration_manager): # <-- NEW
    """Generate STATUS.md with collaboration section."""
    state = state_tracker.get_state()
    system_info = state.get("system_info", {})
    status_content = f"# AI Runtime Steward - Status Report\nGenerated: {time.ctime()}\n"
    status_content += f"## System Status\n- **Phase**: {system_info.get('phase', 'bootstrap')}\n"

    recommendations_md = scheduler.format_recommendations_md()
    status_content += "\n" + recommendations_md + "\n"

    # --- NEW Collaboration Section (Phase 3.3) ---
    collaboration_md = collaboration_manager.format_escalations_md()
    if collaboration_md:
        status_content += collaboration_md + "\n"

    status_content += f"## Available Tasks ({len(task_registry)})\n"
    # ... (rest of the function is the same as Phase 3.2)
    task_history = state.get('task_history', {})
    for task_id, task in task_registry.items():
        status_content += f"\n### {task['name']} (`{task_id}`)\n"
        task_run = task_history.get(task_id)
        if task_run:
            status = '✅ Success' if task_run.get('success') else '❌ Failed'
            status_content += f"- **Last Run**: {time.ctime(task_run['last_run'])} ({status})\n"

    status_content += f"\n*Phase 3.3 - Collaboration & Escalation Enabled*\n"
    with open("STATUS.md", "w") as f:
        f.write(status_content)
    print(f"📄 Status report written to STATUS.md")

def list_available_tasks(task_registry):
    # This function remains the same
    print("\n📋 Available Tasks:")
    for task_id, task in task_registry.items():
        print(f"  {task_id:25} - {task['name']}")

def execute_task_command(task_command, task_registry, task_executor):
    # This function remains the same
    task_id = next((tid for tid, t in task_registry.items() if task_command in tid or task_command in t['name'].lower()), None)
    if not task_id:
        print(f"❌ No task found matching '{task_command}'")
        return
    result = task_executor.execute_task(task_id)

if __name__ == "__main__":
    sys.exit(main())
