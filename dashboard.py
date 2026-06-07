import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

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

    user_input = st.chat_input("Schreibe deine Antwort ...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"messages": st.session_state.chat_messages},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            assistant_text = result.get("message") or result.get("response")
            if not assistant_text:
                assistant_text = "Danke, ich prüfe die Angaben weiter."

            if result.get("status") == "complete":
                assistant_text = result.get("message", assistant_text)

            st.session_state.chat_messages.append({"role": "assistant", "content": assistant_text})
            st.rerun()
        except Exception as e:
            st.session_state.chat_messages.append({"role": "assistant", "content": f"Verbindungsfehler: {e}"})
            st.rerun()

with tab_users:
    st.title("📋 Registrierungen")

    if st.button("🔄 Aktualisieren"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/users", timeout=10)
        users = response.json()
        if users:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("Noch keine Registrierungen vorhanden.")
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
