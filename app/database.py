from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib.parse

Base = declarative_base()

def get_engine():
    from app.config import get_connection_string
    conn_str = get_connection_string()
    parts = dict(item.split("=", 1) for item in conn_str.split(";") if "=" in item)
    server = parts.get("Server", "").replace("tcp:", "").split(",")[0]
    database = parts.get("Database", "")
    user = parts.get("User ID", "")
    password = urllib.parse.quote_plus(parts.get("Password", ""))
    return create_engine(f"mssql+pymssql://{user}:{password}@{server}/{database}")

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
