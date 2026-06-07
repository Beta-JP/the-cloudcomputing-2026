import json
import os
from azure.ai.projects import AIProjectClient
from azure.identity import ManagedIdentityCredential, DefaultAzureCredential

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
SYSTEM_PROMPT = (
    "Du bist ein Registrierungsassistent. Sammle die Nutzerdaten schrittweise und antworte ausschließlich als JSON. "
    "Nutze dieses Format: {\"status\":\"incomplete\"|\"complete\",\"message\":\"...\",\"data\":{...}}. "
    "Pflichtfelder sind: first_name, last_name, birthdate, email, phone, street, house_number, zip_code, city, country. "
    "Wenn noch etwas fehlt, stelle genau die nächste sinnvolle Rückfrage. Wenn alles vorhanden ist, setze status auf complete."
)

def parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)

def get_credential():
    if os.getenv("WEBSITE_SITE_NAME"):
        return ManagedIdentityCredential()
    return DefaultAzureCredential()

def chat_with_agent(messages: list) -> dict:
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    
    client = AIProjectClient(
        endpoint=endpoint,
        credential=get_credential(),
    )

    openai_client = client.get_openai_client()
    chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role in {"user", "assistant"} and content:
            chat_messages.append({"role": role, "content": content})

    response = openai_client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=chat_messages,
        temperature=0.2,
    )

    last = response.choices[0].message.content or ""

    try:
        return parse_json_response(last)
    except json.JSONDecodeError:
        return {"status": "incomplete", "message": last, "collected": {}}
