import json
import os
import re
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

def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" ,.;")

def extract_data_from_messages(messages: list) -> dict:
    combined = "\n".join(msg.get("content", "") for msg in messages if msg.get("content"))
    data = {}

    patterns = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "phone": r"(?:\+?\d[\d\s()/.-]{6,}\d)",
        "birthdate": r"\b(?:\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{2}-\d{2})\b",
        "zip_code": r"\b\d{4,5}\b",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, combined)
        if match:
            data[field] = _clean_value(match.group(0))

    city_match = re.search(r"\b(?:in|aus|aus\s+dem|aus\s+der|wohne\s+in)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+?)(?:[\.,;]|$)", combined)
    if city_match:
        data["city"] = _clean_value(city_match.group(1))

    country_match = re.search(r"\b(?:Deutschland|Österreich|Schweiz|Germany|Austria|Switzerland)\b", combined, flags=re.IGNORECASE)
    if country_match:
        data["country"] = _clean_value(country_match.group(0))

    street_match = re.search(r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+\s+\d+[A-Za-z]?)\b", combined)
    if street_match:
        data["street"] = _clean_value(street_match.group(1))
        house_parts = re.search(r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+)\s+(\d+[A-Za-z]?)\b", street_match.group(1))
        if house_parts:
            data["street"] = _clean_value(house_parts.group(1))
            data["house_number"] = _clean_value(house_parts.group(2))

    first_name_match = re.search(r"\b(?:ich heiße|mein name ist|vorname ist)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)", combined, flags=re.IGNORECASE)
    if first_name_match:
        data["first_name"] = _clean_value(first_name_match.group(1))

    last_name_match = re.search(r"\b(?:nachname ist|ich heiße|mein name ist)\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)", combined, flags=re.IGNORECASE)
    if last_name_match:
        data["last_name"] = _clean_value(last_name_match.group(1))

    return data

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
        result = parse_json_response(last)
        extracted_data = extract_data_from_messages(messages)
        model_data = result.get("data") or {}
        merged_data = {**extracted_data, **model_data}
        result["data"] = merged_data

        if result.get("status") in {"incomplete", "pending_confirmation", "complete"}:
            missing_fields = [field for field, _ in FIELD_ORDER if not merged_data.get(field)]
            if missing_fields and result.get("status") == "complete":
                result["status"] = "pending_confirmation"

        return normalize_result(result)
    except json.JSONDecodeError:
        extracted_data = extract_data_from_messages(messages)
        return normalize_result({"status": "pending_confirmation" if extracted_data else "incomplete", "message": last, "data": extracted_data})
