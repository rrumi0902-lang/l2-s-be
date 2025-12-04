from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.job import JobModel
from datetime import datetime, UTC
from app.api.router_base import router_runpod as router


@router.get("/job/my")
async def get_job_my(request: Request, db: Session = Depends(get_db)):
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

    jobs = db.query(JobModel).filter(JobModel.user_id == user.id).all()
    jobs_data = [
        {
            "job_id": job.id,
            "video_id": job.video_id,
            "method": job.method,
            "status": job.status.value if hasattr(job.status, "value") else job.status,
        }
        for job in jobs
    ]

    return { "jobs": jobs_data }