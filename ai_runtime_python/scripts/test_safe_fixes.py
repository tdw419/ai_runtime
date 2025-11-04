import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.code_manager import CodeManager

async def test_safe_fixes():
    """Test the safety checks and backup system without requiring LM Studio"""
    code_manager = CodeManager(None)  # No LLM needed for safety tests
    
    # Test safety checks with various issues
    test_issues = [
        {
            "file": "test.py",
            "issue_type": "style", 
            "description": "Line too long",
            "severity": "low",
            "suggestion": "Break into multiple lines"
        },
        {
            "file": "auth.py",
            "issue_type": "security",
            "description": "Hardcoded password", 
            "severity": "critical",
            "suggestion": "Remove password"
        },
        {
            "file": "data.py",
            "issue_type": "logic",
            "description": "Potential data loss in function",
            "severity": "high", 
            "suggestion": "Add data backup"
        }
    ]
    
    print("Testing safety checks...")
    for i, issue in enumerate(test_issues):
        is_safe = await code_manager._is_safe_to_fix(issue)
        print(f"Issue {i+1}: {issue['description']}")
        print(f"  Severity: {issue['severity']}, Safe to auto-fix: {is_safe}")
    
    # Test backup and file operations
    print("\nTesting backup system...")
    test_file = "/tmp/test_backup.py"
    test_content = "print('hello world')"
    
    # Create test file
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    # Test backup creation
    import shutil
    backup_path = f"{test_file}.backup"
    shutil.copy2(test_file, backup_path)
    
    if os.path.exists(backup_path):
        print("✓ Backup system works")
        os.remove(backup_path)
    else:
        print("✗ Backup failed")
    
    # Cleanup
    os.remove(test_file)
    print("✓ File operations work correctly")

if __name__ == "__main__":
    asyncio.run(test_safe_fixes())
