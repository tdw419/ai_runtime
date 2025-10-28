# model_client.py
import requests
import time
from typing import Optional

class ModelClient:
    def __init__(self, endpoint: str = "http://localhost:1234/v1/completions", model: Optional[str] = None):
        self.endpoint = endpoint
        self.model = model

    def generate(self, prompt: str, max_retries: int = 3) -> str:
        """Send a prompt to the model and return the response."""
        for attempt in range(max_retries):
            try:
                payload = {
                    "prompt": prompt,
                    "max_tokens": 800,
                    "temperature": 0.4,
                }
                if self.model:
                    payload["model"] = self.model
                resp = requests.post(self.endpoint, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()["choices"][0]["text"]
            except Exception as e:
                if attempt == max_retries - 1:
                    return f'{{"error": "MODEL_UNAVAILABLE", "detail": "{str(e)}"}}'
                time.sleep(1.5)
        return '{"error": "MODEL_UNAVAILABLE", "detail": "Max retries exceeded"}'
