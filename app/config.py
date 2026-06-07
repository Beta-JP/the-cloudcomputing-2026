from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

KEYVAULT_URL = "https://kv-reg-bot-masch.vault.azure.net/"

def get_secret(secret_name: str) -> str:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KEYVAULT_URL, credential=credential)
    return client.get_secret(secret_name).value

def get_connection_string() -> str:
    return get_secret("SqlConnectionString")

def get_ai_key() -> str:
    return get_secret("AiKey")
