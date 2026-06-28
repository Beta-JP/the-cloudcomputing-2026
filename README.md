# Registration Bot

Ein KI-gestützter Registrierungsassistent, der Nutzerdaten per Chat oder Sprache erfasst und in einer Azure SQL-Datenbank speichert.

## Architektur

```
registration-bot-app        (Azure App Service — FastAPI API)
registration-dashboard      (Azure App Service — Streamlit Frontend)
sql-registration-bot        (Azure SQL Server)
registrationdb              (Azure SQL Datenbank)
kv-reg-bot-masch            (Azure Key Vault)
ai-masch-7185-resource      (Azure AI Foundry)
speech-registration-bot     (Azure Speech Service)
```

## Skripte

**startup.sh** — wird von beiden Azure Web Apps als Startbefehl verwendet. Je nach `APP_MODE` startet es entweder nur die API, nur das Frontend oder beides:

- `APP_MODE=api` — startet uvicorn für die FastAPI-Anwendung
- `APP_MODE=frontend` — startet Streamlit für das Dashboard
- `APP_MODE=both` — startet beides (nur für lokale Entwicklung sinnvoll)

**start.sh** — ein Hilfsskript für den lokalen Rechner. Es startet beide Azure Web Apps auf einmal über die Azure CLI, falls sie gestoppt wurden:

```bash
./start.sh
```

## Projektstruktur

```
app/
  main.py          FastAPI-Anwendung mit /chat und /users Endpunkten
  agent.py         Azure AI Foundry Agent-Integration
  config.py        Key Vault Verbindung und Secret-Abruf
  database.py      SQL-Datenbankverbindung via pymssql
  models.py        SQLAlchemy User-Modell
dashboard.py       Streamlit-Frontend mit Chat und Registrierungsliste
startup.sh         Startskript für Azure App Service
start.sh           Hilfsskript zum Starten beider Azure Services
requirements.txt   Python-Abhängigkeiten
infra/             Bicep-Infrastruktur-Templates
.github/           GitHub Actions Deployment-Workflow
```

## Voraussetzungen

- Python 3.12
- Azure CLI (`az login` bereits ausgeführt)
- Ein Azure-Abonnement mit Berechtigung, Ressourcen zu erstellen
- Mikrofon (für Spracheingabe)

## Lokale Einrichtung

```bash
python -m venv antenv
source antenv/bin/activate
pip install -r requirements.txt
```

Umgebungsvariablen setzen:

```bash
export API_URL="https://registration-bot-app.azurewebsites.net"

export AZURE_SPEECH_KEY=$(az cognitiveservices account keys list \
    --name speech-registration-bot \
    --resource-group rg-registration-bot \
    --query "key1" -o tsv)

export AZURE_SPEECH_REGION="swedencentral"
export AZURE_AI_PROJECT_ENDPOINT="https://ai-masch-7185-resource.services.ai.azure.com/api/projects/ai-masch-7185"
```

Frontend starten:

```bash
streamlit run dashboard.py
```

## Azure-Einrichtung

### 1. Resource Group

```bash
az group create \
    --name rg-registration-bot \
    --location swedencentral
```

### 2. SQL Server und Datenbank

```bash
az sql server create \
    --name sql-registration-bot \
    --resource-group rg-registration-bot \
    --location swedencentral \
    --admin-user sqladmin \
    --admin-password "<passwort>"

az sql db create \
    --server sql-registration-bot \
    --resource-group rg-registration-bot \
    --name registrationdb \
    --service-objective Basic
```

### 3. Key Vault

```bash
az keyvault create \
    --name kv-reg-bot-masch \
    --resource-group rg-registration-bot \
    --location swedencentral

az keyvault secret set \
    --vault-name kv-reg-bot-masch \
    --name SqlConnectionString \
    --value "Server=tcp:sql-registration-bot.database.windows.net,1433;Database=registrationdb;User ID=sqladmin;Password=<passwort>;Encrypt=yes;"
```

### 4. Speech Service

```bash
az cognitiveservices account create \
    --name speech-registration-bot \
    --resource-group rg-registration-bot \
    --location swedencentral \
    --kind SpeechServices \
    --sku S0

SpeechKey=$(az cognitiveservices account keys list \
    --name speech-registration-bot \
    --resource-group rg-registration-bot \
    --query "key1" -o tsv)

az keyvault secret set \
    --vault-name kv-reg-bot-masch \
    --name SpeechKey \
    --value "$SpeechKey"
```

### 5. App Service Plan und Web Apps

```bash
az appservice plan create \
    --name asp-registration-bot \
    --resource-group rg-registration-bot \
    --location swedencentral \
    --is-linux \
    --sku B1

az webapp create \
    --resource-group rg-registration-bot \
    --plan asp-registration-bot \
    --name registration-bot-app \
    --runtime "PYTHON|3.12"

az webapp create \
    --resource-group rg-registration-bot \
    --plan asp-registration-bot \
    --name registration-dashboard \
    --runtime "PYTHON|3.12"
```

### 6. Managed Identity aktivieren

```bash
az webapp identity assign \
    --resource-group rg-registration-bot \
    --name registration-bot-app
```

Die ausgegebene `principalId` für die Rollenvergabe notieren.

### 7. RBAC-Rollen vergeben

```bash
PRINCIPAL_ID="<principalId aus Schritt 6>"
SCOPE="/subscriptions/<subscription-id>/resourceGroups/rg-registration-bot"

az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee "$PRINCIPAL_ID" \
    --scope "$SCOPE/providers/Microsoft.KeyVault/vaults/kv-reg-bot-masch"

az role assignment create \
    --role "Azure AI Developer" \
    --assignee "$PRINCIPAL_ID" \
    --scope "$SCOPE"

az role assignment create \
    --role "Cognitive Services OpenAI User" \
    --assignee "$PRINCIPAL_ID" \
    --scope "$SCOPE/providers/Microsoft.CognitiveServices/accounts/ai-masch-7185-resource"
```

### 8. App Settings setzen

API:

```bash
az webapp config appsettings set \
    --resource-group rg-registration-bot \
    --name registration-bot-app \
    --settings \
        APP_MODE=api \
        AZURE_AI_PROJECT_ENDPOINT="https://ai-masch-7185-resource.services.ai.azure.com/api/projects/ai-masch-7185" \
        AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
        AZURE_KEYVAULT_URL="https://kv-reg-bot-masch.vault.azure.net/" \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true

az webapp config set \
    --resource-group rg-registration-bot \
    --name registration-bot-app \
    --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

Dashboard:

```bash
SPEECH_KEY=$(az cognitiveservices account keys list \
    --name speech-registration-bot \
    --resource-group rg-registration-bot \
    --query "key1" -o tsv)

az webapp config appsettings set \
    --resource-group rg-registration-bot \
    --name registration-dashboard \
    --settings \
        APP_MODE=frontend \
        API_URL="https://registration-bot-app.azurewebsites.net" \
        AZURE_SPEECH_KEY="$SPEECH_KEY" \
        AZURE_SPEECH_REGION="swedencentral" \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true

az webapp config set \
    --resource-group rg-registration-bot \
    --name registration-dashboard \
    --startup-file "bash startup.sh"
```

### 9. Deployen

```bash
az webapp up \
    --resource-group rg-registration-bot \
    --name registration-bot-app \
    --runtime "PYTHON:3.12"

az webapp up \
    --resource-group rg-registration-bot \
    --name registration-dashboard \
    --runtime "PYTHON:3.12"
```

## Umgebungsvariablen

| Variable | Beschreibung | Wo gesetzt |
|---|---|---|
| `APP_MODE` | `api`, `frontend` oder `both` | Azure App Settings |
| `API_URL` | URL der FastAPI-Anwendung | Azure App Settings (Dashboard) |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry Projektendpunkt | Azure App Settings (API) |
| `AZURE_OPENAI_DEPLOYMENT` | Name des GPT-Deployments | Azure App Settings (API) |
| `AZURE_KEYVAULT_URL` | URL des Key Vaults | Azure App Settings (API) |
| `AZURE_SPEECH_KEY` | Azure Speech Service Key | Azure App Settings (Dashboard) |
| `AZURE_SPEECH_REGION` | Azure Speech Service Region | Azure App Settings (Dashboard) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` — pip install beim Deployment | Azure App Settings |

## Endpunkte

| Endpunkt | Methode | Beschreibung |
|---|---|---|
| `/` | GET | Statusprüfung |
| `/chat` | POST | Nachricht an den Registrierungsagenten senden |
| `/users` | GET | Alle registrierten Nutzer abrufen |

## Deployment mit GitHub Actions

Voraussetzungen: GitHub Secret `AZURE_WEBAPP_PUBLISH_PROFILE` muss gesetzt sein (aus Azure Portal → App Service → Get publish profile).

Der Workflow in `.github/workflows/deploy.yml` deployt automatisch bei jedem Push auf `main`.

## Troubleshooting

**401 PermissionDenied bei AI Foundry** — RBAC-Rollen prüfen, 5 Minuten auf Propagierung warten.

**Login failed for user 'sqladmin'** — Firewall-Regeln des SQL Servers prüfen, App Service IPs freischalten.

**Container startet nicht** — `az webapp log tail` ausführen und Startup-Befehl prüfen.

**Keine Sprache erkannt** — Mikrofonberechtigungen im Browser prüfen, Speech Key und Region kontrollieren.
