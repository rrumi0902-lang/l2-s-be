import uuid, shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.utility.storage import upload_to_supabase_storage

router = APIRouter(
    prefix="/video",
    tags=["Video"])


UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload/file")
async def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
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

    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    try:
        file_url = await upload_to_supabase_storage(
            file=file,
            filename=unique_filename,
            bucket="videos"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

    video = VideoModel(
        user_id=user.id,
        file_path=str(file_url),
        youtube_id=None
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {
        "message": f"File '{file.filename}' uploaded successfully!",
        "video_id": video.id,
    }
