from fastapi import Request, Depends, Query
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.job import JobModel
from app.model.user import UserModel
from app.model.video import VideoModel
from app.api.router_base import router_video as router


@router.get("/recent")
async def get_recent_videos(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    jobs = db.query(JobModel).order_by(JobModel.created_at).limit(limit).all()
    jobs_data = []
    for job in jobs:
        if job.status == "completed":
            user = db.query(UserModel).filter(UserModel.id == job.user_id).first()
            video = db.query(VideoModel).filter(VideoModel.id == job.video_id).first()
            jobs_data.append({
                "id": job.id,
                "user": user.username,
                "method": job.method,
                "subtitle": job.subtitle,
                "vertical": job.vertical,
                "result_url": job.result_url,
                "thumbnail_path": video.thumbnail_path,
            })

    return {
        "videos": jobs_data,
        "total": len(jobs_data)
    }
