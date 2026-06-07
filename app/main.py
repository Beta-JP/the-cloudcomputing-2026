from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from app.agent import chat_with_agent
from app.database import get_session
from app.models import User
from datetime import date

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    messages = [m.dict() for m in request.messages]

    try:
        result = chat_with_agent(messages)

        if result.get("status") == "complete":
            data = result.get("data", {})
            session = get_session()
            try:
                user = User(
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    birthdate=date.fromisoformat(data.get("birthdate", "2000-01-01")),
                    email=data.get("email"),
                    phone=data.get("phone"),
                    street=data.get("street"),
                    house_number=data.get("house_number"),
                    zip_code=data.get("zip_code"),
                    city=data.get("city"),
                    country=data.get("country")
                )
                session.add(user)
                session.commit()
            finally:
                session.close()

            return {"status": "complete", "message": "Registrierung erfolgreich gespeichert!"}

        return result
    except Exception as exc:
        return {"status": "error", "message": f"Chat fehlgeschlagen: {exc}"}

@app.get("/users")
def get_users():
    session = get_session()
    users = session.query(User).all()
    session.close()
    return [
        {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "city": u.city,
            "created_at": str(u.created_at)
        }
        for u in users
    ]
