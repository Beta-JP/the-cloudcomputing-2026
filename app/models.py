from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    birthdate = Column(Date)
    email = Column(String(255))
    phone = Column(String(50))
    street = Column(String(255))
    house_number = Column(String(20))
    zip_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))
    created_at = Column(DateTime, default=func.now())
