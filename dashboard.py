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

def delete_user(user_id: int) -> dict:
    try:
        response = requests.delete(f"{API_URL}/users/{user_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Zeitüberschreitung beim Löschen."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Verbindung zur API nicht möglich."}
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except Exception:
            detail = e.response.text if e.response is not None else ""
        return {"status": "error", "message": f"API-Fehler: {e.response.status_code}{f' - {detail}' if detail else ''}"}
    except Exception as e:
        return {"status": "error", "message": f"Unbekannter Fehler: {e}"}

def reset_registration():
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "Hallo, ich helfe dir bei der Registrierung. Nenne mir bitte deine Daten Schritt für Schritt.",
        }
    ]
    st.session_state.registration_finished = False
    st.session_state.clear_manual_input = True

def submit_user_input(user_input: str):
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
        st.session_state.registration_finished = True
    else:
        assistant_text = result.get("message", "Danke, ich prüfe die Angaben weiter.")
        st.session_state.chat_messages.append({"role": "assistant", "content": assistant_text})

    st.session_state.clear_manual_input = True

st.set_page_config(page_title="Registration Bot Dashboard", layout="wide")

if "chat_messages" not in st.session_state:
    reset_registration()
if "registration_finished" not in st.session_state:
    st.session_state.registration_finished = False
if "manual_input" not in st.session_state:
    st.session_state.manual_input = ""
if "clear_manual_input" not in st.session_state:
    st.session_state.clear_manual_input = False

tab_chat, tab_users = st.tabs(["💬 Chat", "📋 Registrierungen"])

with tab_chat:
    st.title("Registrierungs-Chat")
    st.caption("Beschreibe deine Angaben einfach in ganzen Sätzen. Ich frage nach, wenn etwas fehlt.")

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if st.session_state.registration_finished:
        st.success("Die Registrierung ist abgeschlossen.")
        if st.button("Neue Registrierung starten"):
            reset_registration()
            st.rerun()
    else:
        if st.session_state.clear_manual_input:
            st.session_state.manual_input = ""
            st.session_state.clear_manual_input = False

        col_input, col_send, col_mic = st.columns([10, 2, 1])
        with col_input:
            st.text_input(
                "Schreibe deine Antwort ...",
                key="manual_input",
                label_visibility="collapsed",
                placeholder="Schreibe oder diktiere deine Antwort ...",
            )
        with col_send:
            send_clicked = st.button("Senden", use_container_width=True)
        with col_mic:
            mic_clicked = st.button("🎤", help="Spracheingabe", use_container_width=True)

        if send_clicked and st.session_state.manual_input.strip():
            submit_user_input(st.session_state.manual_input.strip())
            st.rerun()

        if mic_clicked:
            with st.spinner("Höre zu..."):
                recognized = speech_to_text()
            if recognized:
                submit_user_input(recognized)
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
            for user in users:
                with st.container(border=True):
                    st.subheader(f"{user.get('first_name', '-') } {user.get('last_name', '-') }")
                    st.write(
                        {
                            "Vorname": user.get("first_name", "-"),
                            "Nachname": user.get("last_name", "-"),
                            "Geburtsdatum": user.get("birthdate", "-"),
                            "E-Mail": user.get("email", "-"),
                            "Telefon": user.get("phone", "-"),
                            "Straße": user.get("street", "-"),
                            "Hausnummer": user.get("house_number", "-"),
                            "PLZ": user.get("zip_code", "-"),
                            "Ort": user.get("city", "-"),
                            "Land": user.get("country", "-"),
                            "Erstellt am": user.get("created_at", "-"),
                        }
                    )
                    if st.button("Löschen", key=f"delete_user_{user['id']}", use_container_width=False):
                        delete_result = delete_user(user["id"])
                        if delete_result.get("status") == "deleted":
                            st.success("Eintrag gelöscht.")
                            st.rerun()
                        else:
                            st.error(delete_result.get("message", "Löschen fehlgeschlagen."))
        else:
            st.info("Noch keine Registrierungen vorhanden.")
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
