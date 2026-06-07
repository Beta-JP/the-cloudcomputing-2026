import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

KEYVAULT_URL = os.getenv("AZURE_KEYVAULT_URL", "https://kv-reg-bot-masch.vault.azure.net/")

_client = None

def get_client():
    global _client
    if _client is None:
        credential = DefaultAzureCredential()
        _client = SecretClient(vault_url=KEYVAULT_URL, credential=credential)
    return _client

def get_secret(secret_name: str) -> str:
    # Lokal: Umgebungsvariable nutzen
    env_map = {
        "SqlConnectionString": "AZURE_SQL_CONNECTIONSTRING",
        "AiKey": "AZURE_AI_KEY"
    }
    env_val = os.getenv(env_map.get(secret_name, ""))
    if env_val:
        return env_val
    return get_client().get_secret(secret_name).value

def get_connection_string() -> str:
    return get_secret("SqlConnectionString")

def get_ai_key() -> str:
    return get_secret("AiKey")
