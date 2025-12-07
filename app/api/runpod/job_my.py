from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.job import JobModel
from datetime import datetime, UTC
from app.api.router_base import router_runpod as router
from app.utility.time import utc_now


@router.get("/job/my")
async def get_job_my(request: Request, db: AsyncSession = Depends(get_db)):
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
        select(JobModel).where(JobModel.user_id == user.id)
    )
    jobs = result.scalars().all()

    jobs_data = [
        {
            "job_id": job.id,
            "video_id": job.video_id,
            "method": job.method,
            "subtitle": job.subtitle,
            "vertical": job.vertical,
            "status": job.status.value if hasattr(job.status, "value") else job.status,
            "name": job.name
        }
        for job in jobs
    ]

    return {"jobs": jobs_data}