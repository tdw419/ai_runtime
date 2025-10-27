#!/usr/bin/env python3
"""
Example: Programmatic usage of the AI Runtime System
"""
from ai_runtime import LMStudioRuntimeSession, RuntimeMemory


def example_basic_usage():
    """Basic example: Create a simple project"""
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60)

    # Initialize session
    session = LMStudioRuntimeSession(
        model_name="qwen2.5-coder-7b",  # Change to your model
        lm_base_url="http://localhost:1234",
        project_root="./example_project"
    )

    # Step 1: Create initial structure
    print("\n📝 Step 1: Creating Flask app...")
    result = session.step("Create a simple Flask web server with hello world")
    print(f"✅ Success: {result['success']}")
    print(f"🤖 AI: {result['ai_reasoning']}")

    # Step 2: Add feature
    print("\n📝 Step 2: Adding database...")
    result = session.step("Add SQLite database support with a User model")
    print(f"✅ Success: {result['success']}")

    # Check status
    print("\n📊 Current Status:")
    status = session.get_status()
    print(f"Modules: {len(status['modules'])}")
    print(f"Active steps: {len(status['active_steps'])}")

    session.close()
    print("\n✅ Example completed!")


def example_module_management():
    """Example: Managing modules and freeze states"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Module Management")
    print("=" * 60)

    session = LMStudioRuntimeSession(
        model_name="qwen2.5-coder-7b",
        lm_base_url="http://localhost:1234",
        project_root="./example_project_2"
    )

    # Create auth module
    print("\n📝 Creating auth module...")
    result = session.step("Create user authentication with login and logout")

    # Freeze the auth module
    print("\n🔒 Freezing auth module to protect it...")
    session.freeze_module("auth")

    # Try to modify (should be blocked)
    print("\n📝 Trying to modify frozen module...")
    result = session.step("Update the auth module to add password reset")
    print(f"Result: {result['success']}")

    # Unfreeze
    print("\n🔓 Unfreezing auth module...")
    session.unfreeze_module("auth")

    # Now it should work
    result = session.step("Update the auth module to add password reset")
    print(f"Result: {result['success']}")

    session.close()
    print("\n✅ Example completed!")


def example_database_queries():
    """Example: Querying the database directly"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Database Queries")
    print("=" * 60)

    memory = RuntimeMemory("./example_project/runtime_state.db")

    # Get all modules
    print("\n📋 All Modules:")
    modules = memory.list_modules()
    for mod in modules:
        print(f"  • {mod['name']} [{mod['status']}] - {mod['description']}")

    # Get active steps
    print("\n📋 Active Steps:")
    steps = memory.get_active_steps()
    for step in steps:
        print(f"  • {step['title']} [{step['status']}]")

    # Get recent actions
    print("\n📋 Recent Actions:")
    actions = memory.get_recent_actions(limit=5)
    for action in actions:
        success = "✅" if action['success'] else "❌"
        print(f"  {success} {action['action_type']}")

    # Get context summary for LLM
    print("\n📋 Context Summary:")
    print(memory.get_context_summary())

    memory.close()
    print("\n✅ Example completed!")


def example_incremental_building():
    """Example: Building a project incrementally"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Incremental Building")
    print("=" * 60)

    session = LMStudioRuntimeSession(
        model_name="qwen2.5-coder-7b",
        lm_base_url="http://localhost:1234",
        project_root="./todo_app"
    )

    # Build step by step
    steps = [
        "Create a Flask application structure",
        "Add a Todo model with SQLite database",
        "Create API endpoints for CRUD operations on todos",
        "Add input validation and error handling",
        "Create HTML templates for the frontend",
        "Add CSS styling",
    ]

    for i, step in enumerate(steps, 1):
        print(f"\n📝 Step {i}/{len(steps)}: {step}")
        result = session.step(step)
        if result['success']:
            print(f"  ✅ Completed")
            print(f"  🤖 {result['ai_reasoning'][:80]}...")
        else:
            print(f"  ❌ Failed: {result.get('error')}")
            break

    # Show final status
    status = session.get_status()
    print(f"\n📊 Final Status:")
    print(f"  Modules created: {len(status['modules'])}")
    print(f"  Total actions: {len(status['recent_actions'])}")

    session.close()
    print("\n✅ Example completed!")


if __name__ == "__main__":
    import sys

    print("🤖 AI Runtime System - Examples")
    print("\nChoose an example to run:")
    print("  1. Basic Usage")
    print("  2. Module Management (Freeze/Unfreeze)")
    print("  3. Database Queries")
    print("  4. Incremental Building")
    print("  5. Run All")

    choice = input("\nEnter choice (1-5): ").strip()

    try:
        if choice == "1":
            example_basic_usage()
        elif choice == "2":
            example_module_management()
        elif choice == "3":
            example_database_queries()
        elif choice == "4":
            example_incremental_building()
        elif choice == "5":
            example_basic_usage()
            example_module_management()
            example_database_queries()
            example_incremental_building()
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
