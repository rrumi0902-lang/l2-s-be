from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.utility.youtube import download_youtube_video
from app.utility.storage import upload_file_to_supabase_storage
import tempfile, os

router = APIRouter(
    prefix="/video",
    tags=["Video"]
)

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class YouTubeUploadRequest(BaseModel):
    youtube_id: str


@router.post("/upload/youtube")
async def upload_youtube_video(request: Request, data: YouTubeUploadRequest, db: Session = Depends(get_db)):
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

    # Download YouTube video to temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        file_path, video_title = download_youtube_video(data.youtube_id, Path(temp_dir))

        # Upload to Supabase Storage
        filename = Path(file_path).name
        with open(file_path, 'rb') as f:
            file_content = f.read()

        file_url = await upload_file_to_supabase_storage(
            file_content=file_content,
            filename=filename,
            content_type="video/mp4",
            bucket="videos"
        )

        # Clean up temporary file
        os.remove(file_path)
        os.rmdir(temp_dir)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

    # Save to database
    video = VideoModel(
        user_id=user.id,
        file_path=file_url,  # Store Supabase Storage URL
        youtube_id=data.youtube_id
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {
        "message": f"YouTube video '{video_title}' downloaded and uploaded successfully!",
        "video_id": video.id,
        "file_url": file_url
    }