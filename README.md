# Registration Bot — Setup-Anleitung

Diese Anleitung beschreibt, wie du die Anwendung lokal einrichtest, welche Azure-Ressourcen benötigt werden und wie die benötigten Umgebungsvariablen gesetzt werden.

**Voraussetzungen**
- Python 3.11+ installiert
- Ein Azure-Konto mit Berechtigung, Ressourcen zu erstellen
- Mikrofonzugriff für die Sprachaufnahme

**Projektdateien**
- [dashboard.py](dashboard.py) — Streamlit-Frontend
- [requirements.txt](requirements.txt) — Python-Abhängigkeiten
- [startup.sh](startup.sh) — optionales Start-Skript
- [app/](app/) — Backend-Anwendung

1) Virtuelle Umgebung & Abhängigkeiten

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2) Azure: Speech Service (erforderlich)

- Melde dich im Azure-Portal an.
- Erstelle eine neue Ressource vom Typ **Speech** (oder **Cognitive Services** mit aktivierter Speech-Funktion).
- Wähle eine Region (z. B. `swedencentral`) und notiere dir **Key** und **Region** aus der Übersicht (`Keys and Endpoint`).

Wichtig: Der Schlüssel (Key) ist das, was in der Anwendung als `AZURE_SPEECH_KEY` verwendet wird. Die Region entspricht `AZURE_SPEECH_REGION`.

3) Umgebungsvariablen

Die Anwendung erwartet folgende Umgebungsvariablen (Standardwerte sind im Code angegeben):


Beispiele zum Setzen unter macOS (zsh):

```bash
export API_URL="http://127.0.0.1:8000"
export AZURE_SPEECH_KEY="<dein_speech_key>"
export AZURE_SPEECH_REGION="swedencentral"
```

Schnellstart mit Azure CLI

Wenn du die Azure CLI installiert und angemeldet (`az login`) hast, kannst du den Speech-Key automatisch auslesen und die Umgebungsvariablen setzen (passe Ressourcennamen und Resource-Group an):

```bash
export AZURE_SPEECH_KEY=$(az cognitiveservices account keys list \
	--name speech-registration-bot \
	--resource-group rg-registration-bot \
	--query "key1" -o tsv)

export AZURE_SPEECH_REGION="swedencentral"
export API_URL="https://registration-bot-app.azurewebsites.net"

streamlit run dashboard.py
```

Hinweis: Ersetze `speech-registration-bot` und `rg-registration-bot` durch deine tatsächlichen Azure-Ressourcennamen.


Alternativ kannst du die Variablen in einer Datei `.env` speichern und mit `direnv` oder einem kleinen Loader in die Umgebung laden. Beispiel `.env`:

```
API_URL=http://127.0.0.1:8000
AZURE_SPEECH_KEY=<dein_speech_key>
AZURE_SPEECH_REGION=swedencentral
```

4) Backend starten

Falls das Backend in `app` als FastAPI existiert, starte es mit `uvicorn`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Überprüfe, dass `GET /users` und `POST /chat` erreichbar sind. `dashboard.py` nutzt `API_URL` um diese Endpunkte anzusprechen.

5) Frontend (Streamlit) starten

```bash
streamlit run dashboard.py
```

Die Anwendung öffnet sich im Browser. Erlaube den Zugriff auf das Mikrofon, wenn du Sprachaufnahme testen willst.

6) Hinweise & Troubleshooting

- Fehler beim Verbinden mit Azure: Stelle sicher, dass `AZURE_SPEECH_KEY` und `AZURE_SPEECH_REGION` korrekt sind.
- Keine Sprache erkannt: Prüfe Mikrofonberechtigungen im Browser/OS.
- API-Verbindungsfehler: Prüfe, ob das Backend unter `API_URL` läuft. Standardmäßig erwartet das Frontend `http://127.0.0.1:8000`.

7) Nützliche Links
- Azure Speech docs: https://learn.microsoft.com/azure/cognitive-services/speech-service/

Wenn du möchtest, kann ich eine `.env.example` Datei anlegen oder die README um Anleitungen für Deployment (z. B. Azure App Service) erweitern.
