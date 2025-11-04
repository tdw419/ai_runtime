import aiohttp
import json

class LLMManager:
    def __init__(self, base_url="http://localhost:1234/v1", model="local-model"):
        self.base_url = base_url
        self.model = model
        self.session = None

    async def query(self, prompt, system_prompt=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if not self.session:
            self.session = aiohttp.ClientSession()
         
        async with self.session.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": "local-model",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 500
            }
        ) as response:
            result = await response.json()
        return result['choices'][0]['message']['content']
    
    async def close(self):
        if self.session:
            await self.session.close()