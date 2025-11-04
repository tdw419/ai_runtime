import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.code_manager import CodeManager
from core.llm_manager import LLMManager

async def test_basic_analysis():
    """Test basic code analysis without LM Studio dependency"""
    code_manager = CodeManager(None)  # No LLM manager
    
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"Testing basic code analysis for: {project_path}")
    
    # Test project structure scanning
    structure = await code_manager._scan_project_structure(project_path)
    print("Project Structure:")
    for key, files in structure.items():
        print(f"  {key}: {len(files)} files")
    
    # Test basic analysis
    analysis = code_manager._basic_code_analysis(project_path)
    print(f"Basic Analysis: {analysis['overall_health']}")
    print(f"Python files: {analysis['file_count']}")
    print(f"Test files: {analysis['test_file_count']}")

if __name__ == "__main__":
    asyncio.run(test_basic_analysis())
