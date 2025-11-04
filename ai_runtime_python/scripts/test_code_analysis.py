import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.code_manager import CodeManager
from core.llm_manager import LLMManager
from core.system_prompts import ENHANCED_SYSTEM_PROMPT

async def test_code_analysis():
    """Test the code analysis capabilities"""
    llm_manager = LLMManager()
    try:
        code_manager = CodeManager(llm_manager)
        
        # Test with current project
        project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        print(f"Analyzing code quality for: {project_path}")
        analysis = await code_manager.analyze_code_quality(project_path)
        
        print("Code Analysis Results:")
        print(f"Overall Health: {analysis.get('overall_health', 'unknown')}")
        print(f"Issues Found: {len(analysis.get('issues_found', []))}")
        
        for issue in analysis.get('issues_found', [])[:3]:  # Show first 3 issues
            print(f"  - {issue.get('issue_type')}: {issue.get('description')}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await llm_manager.close()

if __name__ == "__main__":
    asyncio.run(test_code_analysis())