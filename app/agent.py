import json
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

AGENT_ID = "asst_qdIRZcfPLboe5uT9E2HP8xkq"

def chat_with_agent(messages: list) -> dict:
    conn_str = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING") or \
               __import__('app.config', fromlist=['get_secret']).get_secret("AiProjectConnectionString")
    
    client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str
    )
    
    thread = client.agents.create_thread()
    
    for msg in messages:
        if msg["role"] == "user":
            client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=msg["content"]
            )
    
    run = client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=AGENT_ID
    )
    
    response_messages = client.agents.list_messages(thread_id=thread.id)
    last = response_messages.data[0].content[0].text.value
    
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return {"status": "incomplete", "message": last, "collected": {}}
