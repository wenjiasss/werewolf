import os
import json
import requests
from typing import Dict, Any

# Moderate temperature for more consistent results
def generate(model: str, prompt: str, response_schema: Dict[str, Any], temperature: float = 1.0, **kwargs) -> str:
    """Generate text using Ollama local API"""
    
    # Convert our prompt and schema into a chat message
    system_msg = f"""You are an AI assistant playing a game. 

CRITICAL RULES:
1. Your response MUST be valid JSON
2. Start your response with {{ and end with }}
3. Include ALL required fields from the schema
4. Do NOT add any text before or after the JSON

Required JSON schema:
{json.dumps(response_schema, indent=2)}

Example valid response format:
{{"reasoning": "your thinking here", "vote": "PlayerName"}}"""
    
    response = requests.post(
        url="http://localhost:11434/api/chat",
        headers={
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature
            }
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
    result = response.json()
    if "message" not in result or "content" not in result["message"]:
        raise Exception(f"No message content in response: {result}")
        
    return result["message"]["content"]
