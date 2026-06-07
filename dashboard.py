import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Registration Bot Dashboard", layout="wide")
st.title("📋 Registrierungen")

if st.button("🔄 Aktualisieren"):
    st.rerun()

try:
    response = requests.get(f"{API_URL}/users")
    users = response.json()
    if users:
        st.dataframe(users, use_container_width=True)
    else:
        st.info("Noch keine Registrierungen vorhanden.")
except Exception as e:
    st.error(f"Verbindungsfehler: {e}")
