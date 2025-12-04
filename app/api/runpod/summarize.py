from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.video import VideoModel
from app.model.job import JobModel, JobStatus
from datetime import datetime, UTC
from app.config.environments import RUNPOD_URL, RUNPOD_API_KEY, BACKEND_URL
from app.api.router_base import router_runpod as router
import requests, os

class SummarizeRequest(BaseModel):
    video_id: int
    method: Literal["llm_only", "echofusion"]
    subtitle: bool
    vertical: bool


@router.post("/summarize")
async def summarize(request: Request, body: SummarizeRequest, db: Session = Depends(get_db)):
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

    video = db.query(VideoModel).filter(VideoModel.id == body.video_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VIdeo not found"
        )
    
    # Create job record in database
    job = JobModel(
        user_id=user.id,
        video_id=video.id,
        method=body.method,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Send request to RunPod
    try:
        r = requests.post(
            url=f"{RUNPOD_URL}/run",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RUNPOD_API_KEY}"
            },
            json={
                "input": {
                    "webhook_url": f"{BACKEND_URL}/runpod/webhook",
                    "job_id": os.path.splitext(video.file_path.split('/')[-1])[0],
                    "task": "process_video",
                    "video_url": video.file_path,
                    "options": {
                        "method": body.method,
                        "language": "auto"
                    }
                }
            },
            timeout=30
        )
        
        runpod_response = r.json()
        
        # Update job with RunPod's job ID and set status to processing
        if "id" in runpod_response:
            job.runpod_job_id = runpod_response["id"]
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            db.commit()
        
        return {
            "job_id": job.id,
            "runpod_job_id": runpod_response.get("id"),
            "status": job.status,
            "message": "Job submitted successfully"
        }
        
    except requests.exceptions.RequestException as e:
        # Update job status to failed
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to submit job to RunPod: {str(e)}"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job to RunPod: {str(e)}"
        )