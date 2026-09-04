import os
import json
from dotenv import load_dotenv

load_dotenv()

def call_llm(prompt: str) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="You must respond with valid JSON only. No text before or after the JSON. No markdown. No code blocks. Pure JSON object.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        error_response = {
            "status": "خطأ",
            "score": 0,
            "issues": [str(e)],
            "notes": "فشل الاتصال"
        }
        return json.dumps(error_response, ensure_ascii=False)