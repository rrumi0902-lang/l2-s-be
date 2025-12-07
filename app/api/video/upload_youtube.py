from pathlib import Path
from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from app.utility.time import utc_now
from app.utility.youtube import download_youtube_video
from app.utility.storage import upload_file_to_supabase_storage
from app.utility.video import generate_thumbnail
import tempfile, os, uuid, shutil
from app.api.router_base import router_video as router


class YouTubeUploadRequest(BaseModel):
    youtube_id: str


@router.post("/upload/youtube")
async def upload_youtube_video(request: Request, data: YouTubeUploadRequest, db: AsyncSession = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required"
        )

    result = await db.execute(
        select(SessionModel).where(SessionModel.session_token == session_token)
    )
    session = result.scalar_one_or_none()

    if not session or (session.expires_at and session.expires_at < utc_now()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )

    result = await db.execute(
        select(UserModel).where(UserModel.id == session.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    temp_dir = tempfile.mkdtemp()
    try:
        file_path, video_title = download_youtube_video(data.youtube_id, Path(temp_dir))

        video_uuid = uuid.uuid4()
        original_suffix = Path(file_path).suffix
        unique_filename = f"{video_uuid}{original_suffix}"

        with open(file_path, 'rb') as f:
            file_content = f.read()

        file_url = await upload_file_to_supabase_storage(
            file_content=file_content,
            filename=unique_filename,
            content_type="video/mp4",
            bucket="videos"
        )

        thumbnail_filename = f"{video_uuid}.jpg"
        thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

        thumbnail_generated = generate_thumbnail(
            video_path=file_path,
            output_path=thumbnail_path,
            timestamp="00:00:01"
        )

        thumbnail_url = None
        if thumbnail_generated and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as thumb_file:
                thumbnail_content = thumb_file.read()

            thumbnail_url = await upload_file_to_supabase_storage(
                file_content=thumbnail_content,
                filename=thumbnail_filename,
                content_type="image/jpeg",
                bucket="thumbnails"
            )

        os.remove(file_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        os.rmdir(temp_dir)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

    video = VideoModel(
        user_id=user.id,
        file_path=file_url,
        thumbnail_path=thumbnail_url,
        youtube_id=data.youtube_id,
        name=video_title
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    return {
        "message": f"YouTube video '{video_title}' downloaded and uploaded successfully!",
        "video_id": video.id,
        "video_url": file_url,
        "thumbnail_url": thumbnail_url
    }