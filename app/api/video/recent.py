from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.job import JobModel
from app.model.user import UserModel
from app.model.video import VideoModel
from app.api.router_base import router_video as router


@router.get("/recent")
async def get_recent_videos(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(JobModel, UserModel, VideoModel)
        .join(UserModel, JobModel.user_id == UserModel.id)
        .join(VideoModel, JobModel.video_id == VideoModel.id)
        .where(JobModel.status == "completed")
        .where(JobModel.public.is_(True))
        .order_by(JobModel.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    jobs = result.all()

    jobs_data = []
    for job, user, video in jobs:
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