from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime
import os

router = APIRouter(
    prefix="/video",
    tags=["Video"])


@router.delete("/{id}/delete")
async def delete_video(id: int, request: Request, db: Session = Depends(get_db)):
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

    video = db.query(VideoModel).filter(VideoModel.id == id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Check if user owns this video
    if video.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this video"
        )

    # Delete the file from filesystem if it exists
    if os.path.exists(video.file_path):
        try:
            os.remove(video.file_path)
        except Exception as e:
            # Log the error but continue with database deletion
            print(f"Error deleting file {video.file_path}: {str(e)}")

    # Delete the video record from database
    db.delete(video)
    db.commit()

    return {
        "message": "Video deleted successfully",
        "video_id": id
    }
