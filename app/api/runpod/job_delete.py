from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.job import JobModel
from datetime import datetime, UTC
from app.api.router_base import router_runpod as router
from app.utility.storage import delete_from_supabase_storage


@router.delete("/job/{job_id}")
async def delete_job(job_id: str, request: Request, db: Session = Depends(get_db)):
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

    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this job"
        )

    if job.status in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job is still running, can only delete when completed or failed"
        )

    if job.result_path != None:
        try:
            await delete_from_supabase_storage(job.result_path, bucket="outputs")
        except Exception as e:
            print(f"Error deleting result video file from Supabase Storage: {str(e)}")

    return {
        "message": "Job deleted successfully",
        "job_id": job_id
    }