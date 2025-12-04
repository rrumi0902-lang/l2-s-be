from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.job import JobModel
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.utility.storage import delete_from_supabase_storage
from app.api.router_base import router_video as router


@router.delete("/{id}/delete")
async def delete_video(id: int, request: Request, db: Session = Depends(get_db)):
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

    # Check for related jobs
    related_jobs = db.query(JobModel).filter(JobModel.video_id == id).all()

    # Check if any job is still running
    running_jobs = [job for job in related_jobs if job.status in ["pending", "processing"]]
    if running_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete video. {len(running_jobs)} job(s) still running. Please wait for completion or cancel them first."
        )

    # Delete related job result files from storage and jobs from database
    for job in related_jobs:
        if job.result_url:
            try:
                await delete_from_supabase_storage(job.result_url, bucket="outputs")
            except Exception as e:
                print(f"Error deleting job result file from Supabase Storage: {str(e)}")

        db.delete(job)
    # Delete the video file from Supabase Storage
    try:
        await delete_from_supabase_storage(video.file_path, bucket="videos")
    except Exception as e:
        print(f"Error deleting video file from Supabase Storage: {str(e)}")

    # Delete the thumbnail from Supabase Storage
    if video.thumbnail_path:
        try:
            await delete_from_supabase_storage(video.thumbnail_path, bucket="thumbnails")
        except Exception as e:
            print(f"Error deleting thumbnail from Supabase Storage: {str(e)}")

    # Delete the video record from database
    db.delete(video)
    db.commit()

    return {
        "message": "Video and thumbnail deleted successfully",
        "video_id": id
    }