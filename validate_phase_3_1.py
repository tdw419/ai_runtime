# validate_phase_3_1.py
"""
Validation for Phase 3.1 - Proactive Recommendations
"""

def validate_phase_3_1():
    print("🧪 PHASE 3.1 VALIDATION - PROACTIVE RECOMMENDATIONS")
    print("=" * 60)

    try:
        # Test imports
        from system_state_tracker import SystemStateTracker
        from task_registry import TASK_REGISTRY
        from task_scheduler import TaskScheduler

        print("✅ All imports successful")

        # Test scheduler initialization
        tracker = SystemStateTracker()
        scheduler = TaskScheduler(tracker)
        print("✅ Scheduler initialized")

        # Test recommendations generation
        recommendations = scheduler.discover_recommendations()
        print(f"✅ Recommendations generated: {len(recommendations)} tasks")

        # Test markdown formatting
        md_output = scheduler.format_recommendations_md()
        assert "## Recommended Actions" in md_output
        assert "run_task" in md_output
        print("✅ Markdown formatting working")

        # Show what the scheduler recommends
        print("\n📋 Current recommendations:")
        for rec in recommendations:
            print(f"  {rec['name']} - {rec['reason']}")

        print("\n🎉 PHASE 3.1 VALIDATION COMPLETE!")
        print("The steward can now provide proactive recommendations!")
        return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = validate_phase_3_1()
    if not success:
        exit(1)
