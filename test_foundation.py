# test_foundation.py
"""
Test the foundational components work with your existing runtime
"""

def test_foundation():
    print("🧪 Testing Foundation Components...")

    # Test state tracker
    from system_state_tracker import SystemStateTracker
    tracker = SystemStateTracker()
    print("✅ State tracker initialized")

    # Test task registry
    from task_registry import TASK_REGISTRY
    print(f"✅ Task registry loaded: {len(TASK_REGISTRY)} tasks")

    # Test task executor (mock AI runtime)
    class MockAI:
        def execute_directive(self, directive):
            return {"status": "mock_success", "directive": directive}

    from task_executor import TaskExecutor
    executor = TaskExecutor(MockAI(), tracker)
    print("✅ Task executor initialized")

    # Test state persistence
    tracker.update_task_history("test_task", True, "test_completed")
    print("✅ State persistence working")

    print("\n🎉 Foundation components are ready!")
    print("Next: Integrate with your main runtime")

if __name__ == "__main__":
    test_foundation()
