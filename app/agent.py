import json
from openai import AzureOpenAI

ENDPOINT = "https://ai-registration-bot.cognitiveservices.azure.com/"
DEPLOYMENT = "gpt-4o"

SYSTEM_PROMPT = """Du bist ein Registrierungsassistent.

Extrahiere aus der Konversation folgende Felder:
- first_name, last_name, birthdate (YYYY-MM-DD)
- email, phone
- street, house_number, zip_code, city, country

Fehlende Felder fragst du gezielt nach.
Wenn alle Felder vorhanden sind, antworte NUR mit:
{"status": "complete", "data": {...}}

Solange Felder fehlen:
{"status": "incomplete", "message": "...", "collected": {...}}
"""

def chat_with_agent(messages: list) -> dict:
    from app.config import get_ai_key
    client = AzureOpenAI(
        api_key=get_ai_key(),
        azure_endpoint=ENDPOINT,
        api_version="2024-02-01"
    )
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        temperature=0.3
    )
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"status": "incomplete", "message": content, "collected": {}}
