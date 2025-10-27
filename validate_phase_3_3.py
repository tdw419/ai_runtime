# validate_phase_3_3.py
"""
Validation for Phase 3.3: Human-AI Collaboration & Escalation
"""

import os
import sys

def main():
    print("🔍 Validating Phase 3.3: Human-AI Collaboration...")

    # 1. Check collaboration_manager imports
    try:
        from collaboration_manager import CollaborationManager
        print("✅ CollaborationManager imports successfully")
    except ImportError as e:
        print(f"❌ Failed to import CollaborationManager: {e}")
        return False

    # 2. Test collaboration manager creation
    try:
        cm = CollaborationManager("test_escalations.json")
        print("✅ CollaborationManager instantiates correctly")
    except Exception as e:
        print(f"❌ Failed to create CollaborationManager: {e}")
        return False

    # 3. Test escalation creation
    try:
        esc_id = cm.create_escalation(
            task_id="test_task",
            step_description="restart the web server",
            reason="test risky operation",
            context={"test": "data"}
        )
        print(f"✅ Escalation creation works: {esc_id}")
    except Exception as e:
        print(f"❌ Failed to create escalation: {e}")
        return False

    # 4. Test pending escalations
    pending = cm.get_pending_escalations()
    if esc_id in pending:
        print("✅ Pending escalations tracking works")
    else:
        print("❌ Pending escalations not found")
        return False

    # 5. Test escalation resolution
    try:
        success = cm.resolve_escalation(esc_id, "test approval", "approved")
        if success:
            print("✅ Escalation resolution works")
        else:
            print("❌ Escalation resolution failed")
            return False
    except Exception as e:
        print(f"❌ Failed to resolve escalation: {e}")
        return False

    # 6. Test markdown formatting
    try:
        md = cm.format_escalations_md()
        print("✅ Markdown formatting works")
    except Exception as e:
        print(f"❌ Markdown formatting failed: {e}")
        return False

    # Cleanup
    try:
        if os.path.exists("test_escalations.json"):
            os.remove("test_escalations.json")
        if os.path.exists("collaboration"):
            os.rmdir("collaboration")
    except:
        pass

    print("🎉 Phase 3.3 validation passed! Collaboration system is ready.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
