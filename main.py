# main.py
import time
from runtime_core import SelfImprovingRuntime

def main():
    runtime = SelfImprovingRuntime(
        workspace_root="./sandbox_workspace",
        model_endpoint="http://localhost:1234/v1/completions"
    )
    print("🧠 Self-Improving Runtime Booted")
    print("Goal:", runtime.goal)
    print("Workspace:", runtime.workspace_root)
    while True:
        result = runtime.tick()
        print("\n=== RUNTIME TICK RESULT ===")
        print(result)
        if result["state"] in ("DONE", "ERROR"):
            print("Stopping loop.")
            break
        time.sleep(2)

if __name__ == "__main__":
    main()
