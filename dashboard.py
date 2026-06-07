import os
import re
import requests
import streamlit as st
import azure.cognitiveservices.speech as speechsdk

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "swedencentral")

MONTH_MAP = {
    "januar": "01", "februar": "02", "märz": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "dezember": "12"
}

def preprocess_speech(text: str) -> str:
    # @ ersetzen
    text = re.sub(r'\bat\b', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'\bätt\b', '@', text, flags=re.IGNORECASE)

    # Datum: "17. April 2003" → "17.04.2003"
    def replace_month(match):
        day = match.group(1).zfill(2)
        month = MONTH_MAP.get(match.group(2).lower(), match.group(2))
        year = match.group(3)
        return f"{day}.{month}.{year}"

    text = re.sub(
        r'(\d{1,2})\.\s*(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\s*(\d{4})',
        replace_month,
        text,
        flags=re.IGNORECASE
    )

    # "der 17. April 2003" → "17.04.2003"
    text = re.sub(
        r'der\s+(\d{1,2})\.\s*(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\s*(\d{4})',
        replace_month,
        text,
        flags=re.IGNORECASE
    )

    return text

def speech_to_text() -> str:
    try:
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        speech_config.speech_recognition_language = "de-DE"
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = recognizer.recognize_once()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return preprocess_speech(result.text)
        elif result.reason == speechsdk.ResultReason.NoMatch:
            st.warning("Keine Sprache erkannt. Bitte nochmal versuchen.")
        elif result.reason == speechsdk.ResultReason.Canceled:
            st.error("Spracherkennung abgebrochen.")
    except Exception as e:
        st.error(f"Speech-Fehler: {e}")
    return ""

def send_message(messages: list) -> dict:
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"messages": messages},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Zeitüberschreitung – bitte nochmal versuchen."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Verbindung zur API nicht möglich."}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"API-Fehler: {e.response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Unbekannter Fehler: {e}"}

st.set_page_config(page_title="Registration Bot Dashboard", layout="wide")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "Hallo, ich helfe dir bei der Registrierung. Nenne mir bitte deine Daten Schritt für Schritt.",
        }
    ]

tab_chat, tab_users = st.tabs(["💬 Chat", "📋 Registrierungen"])

with tab_chat:
    st.title("Registrierungs-Chat")
    st.caption("Beschreibe deine Angaben einfach in ganzen Sätzen. Ich frage nach, wenn etwas fehlt.")

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Aufnehmen"):
            with st.spinner("Höre zu..."):
                recognized = speech_to_text()
                if recognized:
                    st.session_state["speech_input"] = recognized
                    st.rerun()

    with col2:
        user_input = st.chat_input("Schreibe oder spreche deine Antwort ...")

    if "speech_input" in st.session_state and st.session_state["speech_input"]:
        user_input = st.session_state.pop("speech_input")

    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        result = send_message(st.session_state.chat_messages)

        if result.get("status") == "error":
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": f"⚠️ {result.get('message')}"
            })
        elif result.get("status") == "complete":
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": result.get("message", "✅ Registrierung erfolgreich gespeichert!")
            })
        else:
            assistant_text = result.get("message", "Danke, ich prüfe die Angaben weiter.")
            st.session_state.chat_messages.append({"role": "assistant", "content": assistant_text})

        st.rerun()

with tab_users:
    st.title("📋 Registrierungen")

    if st.button("🔄 Aktualisieren"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/users", timeout=10)
        response.raise_for_status()
        users = response.json()
        if users:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("Noch keine Registrierungen vorhanden.")
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
