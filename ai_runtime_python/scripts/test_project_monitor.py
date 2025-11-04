import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.project_monitor import ProjectMonitor

async def test_project_monitor():
    config = {
        "projects": [
            {"path": "~/zion/projects/ai_runtime", "name": "AI Runtime"},
            {"path": "/tmp/test_nonexistent", "name": "Nonexistent"}
        ]
    }
    
    monitor = ProjectMonitor(config)
    results = await monitor.scan_all_projects()
    
    for path, state in results.items():
        print(f"Project: {path}")
        print(f"  Exists: {state.exists}")
        print(f"  Git: {state.git_status}")
        print(f"  Recent changes: {len(state.recent_changes or [])}")
        print(f"  Dependencies: {state.dependency_count}")
        print(f"  Test status: {state.test_status}")
        print(f"  Errors: {state.error_count}")
        print()

if __name__ == "__main__":
    asyncio.run(test_project_monitor())
