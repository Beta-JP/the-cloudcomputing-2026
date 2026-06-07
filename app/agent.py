import json
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

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
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def get_project_endpoint() -> str:
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if endpoint:
        return endpoint

    secret_provider = __import__('app.config', fromlist=['get_secret'])
    for secret_name in ("AiProjectEndpoint", "AiProjectConnectionString"):
        try:
            secret_value = secret_provider.get_secret(secret_name)
        except Exception:
            continue

        if not secret_value:
            continue

        parts = dict(item.split("=", 1) for item in secret_value.split(";") if "=" in item)
        for key in ("Endpoint", "ProjectEndpoint", "AIProjectEndpoint"):
            candidate = parts.get(key)
            if candidate:
                return candidate.rstrip("/")

        if secret_value.startswith("http://") or secret_value.startswith("https://"):
            return secret_value.rstrip("/")

    raise ValueError(
        "Kein Azure AI Project Endpoint gefunden. Setze AZURE_AI_PROJECT_ENDPOINT oder speichere AiProjectEndpoint im Key Vault."
    )

def chat_with_agent(messages: list) -> dict:
    client = AIProjectClient(
        endpoint=get_project_endpoint(),
        credential=DefaultAzureCredential(),
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
