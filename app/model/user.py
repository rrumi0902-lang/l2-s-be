from sqlalchemy import Column, Integer, String, text
from app.db.database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    credit = Column(Integer, nullable=False, server_default=text("0"))