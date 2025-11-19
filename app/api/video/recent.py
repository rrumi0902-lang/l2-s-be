from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime

router = APIRouter(
    prefix="/videos",
    tags=["Video"])


@router.get("/recent")
async def get_recent_videos(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required"
        )

    session = db.query(SessionModel).filter(SessionModel.session_token == session_token).first()
    if not session or (session.expires_at and session.expires_at < datetime.utcnow()):
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

    # Get recent videos from all users, ordered by ID (most recent first)
    videos = db.query(VideoModel).order_by(VideoModel.id.desc()).limit(limit).all()

    return {
        "videos": [
            {
                "id": video.id,
                "user_id": video.user_id,
                "youtube_id": video.youtube_id,
                "file_path": video.file_path,
            }
            for video in videos
        ],
        "total": len(videos)
    }
