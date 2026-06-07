from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def parse_connection_string(conn_str: str) -> dict:
    result = {}
    for part in conn_str.strip().rstrip(";").split(";"):
        if "=" in part:
            key, _, value = part.partition("=")
            result[key.strip()] = value.strip()
    return result

def get_engine():
    from app.config import get_connection_string
    conn_str = get_connection_string()
    parts = parse_connection_string(conn_str)
    
    url = URL.create(
        drivername="mssql+pymssql",
        username=parts.get("User ID"),
        password=parts.get("Password"),
        host=parts.get("Server", "").replace("tcp:", "").split(",")[0],
        database=parts.get("Database")
    )
    return create_engine(url)

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
