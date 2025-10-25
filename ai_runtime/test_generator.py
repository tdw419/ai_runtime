import ast
import inspect
from typing import Dict, Any, List, Optional
from pathlib import Path

class TestGenerator:
    """Automatically generate tests for AI-created code"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.test_dir = self.project_root / "tests"
        self.test_dir.mkdir(exist_ok=True)

    def analyze_code_for_testing(self, filepath: str, code: str) -> Dict[str, Any]:
        """Analyze code to determine what tests are needed"""
        try:
            tree = ast.parse(code)
            functions = []
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "lineno": node.lineno
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "lineno": node.lineno
                    })

            return {
                "success": True,
                "filepath": filepath,
                "functions": functions,
                "classes": classes,
                "needs_tests": len(functions) > 0 or len(classes) > 0
            }
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}

    def generate_test_file(self, analysis: Dict[str, Any]) -> str:
        """Generate pytest test file based on code analysis"""
        filepath = analysis["filepath"]
        filename = Path(filepath).stem

        imports = [
            "import pytest",
            f"from {Path(filepath).stem} import *"
        ]

        test_cases = []

        # Generate test cases for functions
        for func in analysis.get("functions", []):
            if not func["name"].startswith("_"):  # Skip private methods
                test_case = f"""

def test_{func['name']}():
    \"\"\"Test {func['name']} function\"\"\"
    # TODO: Implement test for {func['name']}
    # Example: result = {func['name']}(...)
    # assert result == expected_value
    pass
"""
                test_cases.append(test_case)

        # Generate test cases for classes
        for cls in analysis.get("classes", []):
            test_case = f"""

class Test{cls['name']}:
    \"\"\"Test {cls['name']} class\"\"\"

    def test_{cls['name'].lower()}_creation(self):
        \"\"\"Test {cls['name']} instantiation\"\"\"
        # TODO: Implement test
        # instance = {cls['name']}(...)
        # assert instance is not None
        pass
"""
                test_cases.append(test_case)

        test_content = "\n".join(imports) + "\n".join(test_cases)
        return test_content

    def should_generate_tests(self, filepath: str, action: str) -> bool:
        """Determine if tests should be generated for this action"""
        if action not in ["create_file", "modify_file"]:
            return False

        if not filepath.endswith(".py"):
            return False

        # Don't generate tests for test files
        if "test_" in filepath or filepath.startswith("tests/"):
            return False

        return True
