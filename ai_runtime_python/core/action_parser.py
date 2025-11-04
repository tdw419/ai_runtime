import json

class ActionParser:
    def parse(self, llm_output):
        try:
            data = json.loads(llm_output)
            
            # Validate required fields
            required = ["analysis", "confidence", "recommended_action", "reasoning", "risk_level"]
            if not all(field in data for field in required):
                return {"error": f"Missing required fields in LLM response: {llm_output}"}
            
            return data
        except json.JSONDecodeError:
            # Try to extract JSON from thinking tags or other text
            import re
            json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            return {"error": f"Invalid JSON response from LLM: {llm_output}"}