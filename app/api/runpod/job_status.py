from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.job import JobModel
from datetime import datetime, UTC
from app.api.router_base import router_runpod as router


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str, request: Request, db: Session = Depends(get_db)):
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

    # Find job
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns this job
    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this job"
        )
    
    return {
        "video_id": job.video_id,
        "status": job.status,
        "method": job.method,
        "subtitle": job.subtitle,
        "vertical": job.vertical,
        "result_url": job.result_url,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }