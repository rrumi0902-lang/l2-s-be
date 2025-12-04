from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base

class VideoModel(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    youtube_id = Column(String, nullable=True)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    file_path = Column(String, nullable=False)