# validate_phase_3_2.py
"""
Validation for Phase 3.2 - Natural Language Task Routing
"""

def validate_phase_3_2():
    print("🧪 PHASE 3.2 VALIDATION - NATURAL LANGUAGE ROUTING")
    print("=" * 60)

    try:
        from system_state_tracker import state_tracker
        from task_executor import TaskExecutor
        from task_runner import TaskRunner

        print("✅ Core components imported")

        class MockAI:
            def execute_directive(self, directive):
                return {"success": True, "status": "success", "message": f"Mocked: {directive}"}

        ai_runtime = MockAI()
        task_executor = TaskExecutor(ai_runtime, state_tracker)
        task_runner = TaskRunner(task_executor)

        print("✅ TaskRunner initialized")

        # Test 1: Confident match
        print("\n1. Testing confident command ('check health')...")
        result = task_runner.run_from_text("check health")
        assert result.get("success"), "Should succeed on confident match"
        assert result.get("interpreted_task_id") == "system_health_audit", "Should map to correct task"
        print(f"   ✅ Correctly mapped to '{result['interpreted_task_name']}' with score {result['match_score']}")

        # Test 2: Alias match
        print("\n2. Testing alias command ('system audit')...")
        result = task_runner.run_from_text("system audit")
        assert result.get("success"), "Should succeed on alias match"
        assert result.get("interpreted_task_id") == "system_health_audit", "Should map to correct task via alias"
        print(f"   ✅ Correctly mapped to '{result['interpreted_task_name']}' via alias")

        # Test 3: Graceful refusal
        print("\n3. Testing graceful refusal ('are we ok?')...")
        result = task_runner.run_from_text("are we ok?")
        assert not result.get("success"), "Should fail gracefully on non-confident match"
        assert result.get("error"), "Should provide a helpful error message"
        print(f"   ✅ Correctly refused with hint: {result.get('hint')}")

        print("\n🎉 PHASE 3.2 VALIDATION COMPLETE!")
        print("The steward can now interpret natural language commands.")
        return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = validate_phase_3_2()
    if not success:
        exit(1)
