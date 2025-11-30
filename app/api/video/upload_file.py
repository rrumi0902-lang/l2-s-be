import uuid, tempfile, os
from pathlib import Path
from fastapi import UploadFile, File, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.utility.storage import upload_file_to_supabase_storage
from app.config.environments import RUNPOD_URL, RUNPOD_API_KEY
from app.api.router_base import router_video as router
from fastapi.concurrency import run_in_threadpool
import requests


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
    video_uuid = str(uuid.uuid4())
    unique_filename = f"{video_uuid}{file_extension}"

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    temp_video_path = os.path.join(temp_dir, unique_filename)

    try:
        # Save uploaded file streaming
        with open(temp_video_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)

        # Upload to Supabase via file stream
        with open(temp_video_path, "rb") as f:
            file_url = await run_in_threadpool(
                upload_file_to_supabase_storage,
                file=f,
                filename=unique_filename,
                bucket="videos",
                content_type=file.content_type
            )

        requests.post(
            url=f"{RUNPOD_URL}/run",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RUNPOD_API_KEY}"
            },
            json={
                "input": {
                    "job_id": video_uuid,
                    "task": "generate_thumbnail",
                    "video_url": file_url
                }
            }
        )

    except Exception as e:
        # Clean up temporary files
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

    finally:
        # Clean up temporary files
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


    thumbnail_url = file_url.replace("/videos/", "/thumbnails/")
    if thumbnail_url.endswith(".mp4"):
        thumbnail_url = thumbnail_url[:-4] + ".jpg"

    result_url = file_url.replace("/videos/", "/outputs/")
    if result_url.endswith(".mp4"):
        result_url = result_url[:-4]

    # Save to database
    video = VideoModel(
        user_id=user.id,
        file_path=str(file_url),
        thumbnail_path=thumbnail_url,
        youtube_id=None,
        result_path=result_url
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {
        "message": f"File '{file.filename}' uploaded successfully!",
        "video_id": video.id,
        "video_url": file_url,
        "thumbnail_url": thumbnail_url,
    }