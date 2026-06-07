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

def parse_date(date_str: str) -> date:
    # Versuche verschiedene Formate
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return date.fromisoformat(date_str) if fmt == "%Y-%m-%d" else date(*reversed([int(x) for x in date_str.split("." if "." in date_str else "/")]))
        except Exception:
            continue
    raise ValueError(f"Unbekanntes Datumsformat: {date_str}")

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/chat")
def chat(request: ChatRequest):
    messages = [m.dict() for m in request.messages]
    result = chat_with_agent(messages)

    if result.get("status") == "complete":
        data = result["data"]
        session = get_session()
        try:
            birthdate_str = data.get("birthdate", "2000-01-01")
            if "." in birthdate_str:
                parts = birthdate_str.split(".")
                birthdate = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                birthdate = date.fromisoformat(birthdate_str)

            user = User(
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                birthdate=birthdate,
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
            session.close()
            return {"status": "complete", "message": result.get("message", "Registrierung erfolgreich!")}
        except Exception as e:
            session.rollback()
            session.close()
            return {"status": "error", "message": str(e)}

    if result.get("status") == "pending_confirmation":
        return {
            "status": "pending_confirmation",
            "message": result.get(
                "message",
                "Ich habe alle Angaben erfasst. Bitte prüfe die Zusammenfassung und bestätige, ob alles korrekt ist.",
            ),
            "data": result.get("data", {}),
        }

    return result

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
