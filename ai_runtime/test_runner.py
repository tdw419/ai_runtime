import subprocess
from typing import Dict, Any

class TestRunner:
    def __init__(self, project_root: str):
        self.project_root = project_root

    def run_tests(self, test_path: str = "tests/") -> Dict[str, Any]:
        """Run pytest and return detailed results"""
        try:
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                "success": result.returncode == 0,
                "passed": "passed" in result.stdout,
                "output": result.stdout,
                "failures": self._parse_failures(result.stdout)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_failures(self, pytest_output: str) -> list[str]:
        """Extract test failure details from pytest output"""
        failures = []
        lines = pytest_output.split('\n')
        for i, line in enumerate(lines):
            if "FAILED" in line:
                # Get context around failure
                context = lines[max(0, i-2):min(len(lines), i+3)]
                failures.append('\n'.join(context))
        return failures
