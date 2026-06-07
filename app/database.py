from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_connection_string
import urllib

def get_engine():
    conn_str = get_connection_string()
    params = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine

Base = declarative_base()

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
