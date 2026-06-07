import json
import os
from azure.ai.projects import AIProjectClient
from azure.identity import ManagedIdentityCredential, DefaultAzureCredential

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
FIELD_ORDER = [
    ("first_name", "Vorname"),
    ("last_name", "Nachname"),
    ("birthdate", "Geburtsdatum"),
    ("email", "E-Mail"),
    ("phone", "Telefon"),
    ("street", "Straße"),
    ("house_number", "Hausnummer"),
    ("zip_code", "PLZ"),
    ("city", "Ort"),
    ("country", "Land"),
]
SYSTEM_PROMPT = (
    "Du bist ein Registrierungsassistent. Sammle die Nutzerdaten schrittweise und antworte ausschließlich als JSON. "
    "Nutze dieses Format: {\"status\":\"incomplete\"|\"pending_confirmation\"|\"complete\",\"message\":\"...\",\"data\":{...}}. "
    "Pflichtfelder sind: first_name, last_name, birthdate, email, phone, street, house_number, zip_code, city, country. "
    "Wenn noch etwas fehlt, stelle genau die nächste sinnvolle Rückfrage. "
    "Wenn alle Pflichtfelder vorhanden sind, aber der Nutzer die Zusammenfassung noch nicht ausdrücklich bestätigt hat, setze status auf pending_confirmation. "
    "Gib dann eine kurze, übersichtliche Zusammenfassung aller aufgenommenen Daten aus und frage am Ende explizit, ob alles korrekt ist. "
    "Setze status nur dann auf complete, wenn der Nutzer die Zusammenfassung ausdrücklich bestätigt."
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

def format_summary(data: dict) -> str:
    lines = ["Ich habe folgende Angaben aufgenommen:"]
    for key, label in FIELD_ORDER:
        value = data.get(key)
        if value not in {None, ""}:
            lines.append(f"- {label}: {value}")
    lines.append("Ist das alles korrekt?")
    return "\n".join(lines)

def normalize_result(result: dict) -> dict:
    status = result.get("status")
    data = result.get("data") or {}

    if status == "pending_confirmation":
        result["message"] = format_summary(data)
    elif status == "complete" and not result.get("message"):
        result["message"] = "Registrierung erfolgreich!"
    elif status == "pending_confirmation" and not result.get("message"):
        result["message"] = "Ich habe alle Angaben erfasst. Bitte prüfe die Zusammenfassung und bestätige, ob alles korrekt ist."

    return result

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
        return normalize_result(parse_json_response(last))
    except json.JSONDecodeError:
        return {"status": "incomplete", "message": last, "collected": {}}
