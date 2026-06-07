import urllib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine():
    from app.config import get_connection_string
    conn_str = get_connection_string()
    params = urllib.parse.quote_plus(conn_str)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
