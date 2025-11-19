from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime
from pathlib import Path
import os

router = APIRouter(
    prefix="/video",
    tags=["Video"])


@router.get("/download")
async def download_video(
    video_id: int = Query(..., description="Video ID to download"),
    request: Request = None,
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

    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Check if user owns this video
    if video.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to download this video"
        )

    # Check if file exists
    if not os.path.exists(video.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found on server"
        )

    # Get filename from path
    filename = Path(video.file_path).name

    return FileResponse(
        path=video.file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
