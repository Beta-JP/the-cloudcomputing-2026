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

8) Deployment mit Bicep und Azure Pipelines

Ich habe dir dafür jetzt zwei Dateien angelegt:

- [infra/main.bicep](infra/main.bicep)
- [azure-pipelines.yml](azure-pipelines.yml)

Die Bicep-Datei legt die Basis-Infrastruktur an:

- App Service Plan und zwei Linux Web Apps
- Eine Web App für die API
- Eine separate Web App für das Streamlit-Frontend
- Key Vault mit Secrets für SQL, Speech und Azure AI
- Azure SQL Server und Datenbank
- Speech-Ressource
- Azure AI Services-Ressource
- Application Insights

Die API-Web-App startet `startup.sh` im Modus `api`.
Die Frontend-Web-App startet `startup.sh` im Modus `frontend` und bekommt die `API_URL` der API-Web-App mit.

So funktioniert die Pipeline:

1. Ein `what-if` prüft zuerst, was die Bicep-Datei ändern würde.
2. Danach wird die Infrastruktur mit `az deployment group create` ausgerollt.
3. Anschließend wird der komplette Quellcode als ZIP gepackt.
4. Das ZIP wird per `zipDeploy` zuerst in die API-Web-App und danach in die Frontend-Web-App geladen.

Was du in der Pipeline noch anpassen musst:

- `azureServiceConnection`
- `resourceGroupName`
- `aiProjectEndpoint`
- `sqlAdminPassword` als geheime Pipeline-Variable oder über eine Variable Group
- `apiWebAppName` und `frontendWebAppName`

Wenn du Azure DevOps verwendest, brauchst du also nur noch eine Service Connection und die Secret-Variable für das SQL-Passwort.

9) Deployment mit GitHub Actions

Wenn dein Repo auf GitHub liegt, kannst du stattdessen auch direkt die Datei [/.github/workflows/deploy.yml](.github/workflows/deploy.yml) verwenden.

Benötigte GitHub-Secrets:

- `AZURE_CREDENTIALS` — JSON für den Azure Login in GitHub Actions
- `SQL_ADMIN_PASSWORD` — Passwort für den SQL-Administrator
- `AZURE_AI_PROJECT_ENDPOINT` — Azure AI Foundry Projekt-Endpunkt

Die Workflow-Datei macht dann automatisch:

1. `az login` über `AZURE_CREDENTIALS`
2. `what-if` für die Bicep-Datei
3. `az deployment group create` für die Infrastruktur
4. Zip-Deploy auf die API-Web-App
5. Zip-Deploy auf die Frontend-Web-App

Schritt 1: AZURE_CREDENTIALS erzeugen

Erzeuge einen Service Principal mit Zugriff auf deine Resource Group. Ersetze die Platzhalter durch deine echten Werte:

```bash
az ad sp create-for-rbac \
	--name "github-actions-registration-bot" \
	--role contributor \
	--scopes /subscriptions/<deine-subscription-id>/resourceGroups/rg-registration-bot \
	--sdk-auth
```

Die Ausgabe kopierst du als komplettes JSON in GitHub unter Settings > Secrets and variables > Actions > New repository secret mit dem Namen AZURE_CREDENTIALS.

Wenn du das JSON lokal sichern willst, kannst du es auch in eine Datei schreiben:

```bash
az ad sp create-for-rbac \
	--name "github-actions-registration-bot" \
	--role contributor \
	--scopes /subscriptions/<deine-subscription-id>/resourceGroups/rg-registration-bot \
	--sdk-auth > azure-credentials.json
```

Schritt 2: GitHub-Repository für Actions prüfen

- Öffne im GitHub-Repo die Einstellungen unter Settings > Actions > General.
- Stelle sicher, dass Actions für das Repository erlaubt sind.
- Unter Settings > Secrets and variables > Actions legst du die Secrets AZURE_CREDENTIALS, SQL_ADMIN_PASSWORD und AZURE_AI_PROJECT_ENDPOINT an.
- Prüfe, dass dein Branch main heißt oder passe den Trigger in [/.github/workflows/deploy.yml](.github/workflows/deploy.yml) an.

Wenn du möchtest, kann ich eine `.env.example` Datei anlegen oder die README um Anleitungen für Deployment (z. B. Azure App Service) erweitern.
