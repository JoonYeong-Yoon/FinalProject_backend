from sqlalchemy import Column, String
from db.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "home_training"}

    email = Column(String, primary_key=True, index=True)
    password_hash = Column(String)
    name = Column(String)
