import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_manager import LLMManager
from core.system_prompts import ENHANCED_SYSTEM_PROMPT

async def test_llm():
    llm = LLMManager()
    
    try:
        # Test system admin prompt
        response = await llm.query(
            "CPU is at 95%, memory at 80%, disk at 60%",
            system_prompt=ENHANCED_SYSTEM_PROMPT
        )
        print("LM Studio Response:", response)
    finally:
        await llm.close()

if __name__ == "__main__":
    asyncio.run(test_llm())