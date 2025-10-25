from typing import Dict, Any

def mission_intake(memory) -> Dict[str, Any]:
    """Simple mission intake for demo"""
    print("\n🎯 MISSION INTAKE")
    print("=================")

    mission = input("What should I build? ").strip()
    if not mission:
        mission = "a calculator module with basic math operations"
        print(f"Using default mission: {mission}")

    module = memory.get_or_create_module("main", ".", mission)
    step = memory.create_step(module["id"], f"Build {mission}", mission)

    print(f"✅ Mission: {mission}")
    print(f"📝 Step ID: {step['id']}")
    return {"step": step}
