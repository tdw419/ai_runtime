import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.code_manager import CodeManager
from core.llm_manager import LLMManager

async def test_auto_fix():
    """Test automated code fixing capabilities"""
    llm_manager = LLMManager()
    code_manager = CodeManager(llm_manager)
    
    # Create a test file with a simple issue
    test_content = '''
def calculate_sum(a, b):
    # Missing return statement
    result = a + b
    
def unused_function():
    return "This function is never used"
'''
    
    test_file = "/tmp/test_fix.py"
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    # Create a test issue
    test_issue = {
        "file": "test_fix.py",
        "issue_type": "logic",
        "description": "Function calculate_sum has no return statement",
        "severity": "low",
        "suggestion": "Add return statement"
    }
    
    print("Testing automated fixing...")
    success = await code_manager._apply_single_fix(test_issue, "/tmp")
    print(f"Fix applied: {success}")
    
    if success:
        with open(test_file, 'r') as f:
            print("Fixed content:")
            print(f.read())
    
    await llm_manager.close()

if __name__ == "__main__":
    asyncio.run(test_auto_fix())
