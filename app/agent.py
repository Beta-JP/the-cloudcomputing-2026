import json
import os
from azure.ai.projects import AIProjectClient
from azure.identity import ManagedIdentityCredential, DefaultAzureCredential

AGENT_ID = os.getenv("AZURE_AGENT_ID", "asst_qdIRZcfPLboe5uT9E2HP8xkq")

def get_credential():
    if os.getenv("WEBSITE_SITE_NAME"):
        return ManagedIdentityCredential()
    return DefaultAzureCredential()

def parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)

def chat_with_agent(messages: list) -> dict:
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    client = AIProjectClient(
        endpoint=endpoint,
        credential=get_credential(),
    )

    thread = client.agents.create_thread()

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user" and content:
            client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=content
            )

    run = client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=AGENT_ID
    )

    response_messages = client.agents.list_messages(thread_id=thread.id)
    last = response_messages.data[0].content[0].text.value

    try:
        return parse_json_response(last)
    except json.JSONDecodeError:
        return {"status": "incomplete", "message": last, "collected": {}}
