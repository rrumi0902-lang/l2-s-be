import uuid, tempfile, os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.utility.storage import upload_to_supabase_storage, upload_file_to_supabase_storage
from app.utility.video import generate_thumbnail

router = APIRouter(
    prefix="/video",
    tags=["Video"])


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
    thumbnail_filename = f"{video_uuid}.jpg"

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    temp_video_path = os.path.join(temp_dir, unique_filename)
    temp_thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

    try:
        # Save uploaded file temporarily
        with open(temp_video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Upload video to Supabase Storage
        await file.seek(0)  # Reset file pointer
        file_url = await upload_to_supabase_storage(
            file=file,
            filename=unique_filename,
            bucket="videos"
        )

        # Generate thumbnail using FFmpeg
        thumbnail_generated = generate_thumbnail(
            video_path=temp_video_path,
            output_path=temp_thumbnail_path,
            timestamp="00:00:01"  # Extract frame at 1 second
        )

        thumbnail_url = None
        if thumbnail_generated and os.path.exists(temp_thumbnail_path):
            # Upload thumbnail to Supabase Storage
            with open(temp_thumbnail_path, 'rb') as thumb_file:
                thumbnail_content = thumb_file.read()

            thumbnail_url = await upload_file_to_supabase_storage(
                file_content=thumbnail_content,
                filename=thumbnail_filename,
                content_type="image/jpeg",
                bucket="thumbnails"
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

    # Save to database
    video = VideoModel(
        user_id=user.id,
        file_path=str(file_url),
        thumbnail_path=thumbnail_url,  # Store thumbnail URL
        youtube_id=None
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {
        "message": f"File '{file.filename}' uploaded successfully!",
        "video_id": video.id,
        "video_url": file_url,
        "thumbnail_url": thumbnail_url
    }