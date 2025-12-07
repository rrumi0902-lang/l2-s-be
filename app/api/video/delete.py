from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.job import JobModel
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from app.utility.storage import delete_from_supabase_storage
from app.api.router_base import router_video as router
from app.utility.time import utc_now


@router.delete("/{id}/delete")
async def delete_video(id: int, request: Request, db: AsyncSession = Depends(get_db)):
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

    result = await db.execute(
        select(VideoModel).where(VideoModel.id == id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    if video.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this video"
        )

    result = await db.execute(
        select(JobModel).where(JobModel.video_id == id)
    )
    related_jobs = result.scalars().all()

    running_jobs = [job for job in related_jobs if job.status in ["pending", "processing"]]
    if running_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete video. {len(running_jobs)} job(s) still running."
        )

    for job in related_jobs:
        if job.result_url:
            try:
                await delete_from_supabase_storage(job.result_url, bucket="outputs")
            except Exception as e:
                print(f"Error deleting job result file: {str(e)}")
        await db.delete(job)

    try:
        await delete_from_supabase_storage(video.file_path, bucket="videos")
    except Exception as e:
        print(f"Error deleting video file: {str(e)}")

    if video.thumbnail_path:
        try:
            await delete_from_supabase_storage(video.thumbnail_path, bucket="thumbnails")
        except Exception as e:
            print(f"Error deleting thumbnail: {str(e)}")

    await db.delete(video)
    await db.commit()

    return {
        "message": "Video and thumbnail deleted successfully",
        "video_id": id
    }