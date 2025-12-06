from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.api.router_base import router_video as router


class RenameRequest(BaseModel):
    video_id: str
    name: str

@router.patch("/rename")
async def rename(request: Request, data: RenameRequest, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required"
        )

    session = db.query(SessionModel).filter(SessionModel.session_token == session_token).first()
    if not session or (session.expires_at and session.expires_at < datetime.now(UTC)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )

    user = db.query(UserModel).filter(UserModel.id == session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    video = db.query(VideoModel).filter(VideoModel.id == data.video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    video.name = data.name
    db.commit()
    db.refresh(video)

    return {
        "message": f"Video renamed to {video.name}",
    }

