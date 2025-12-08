from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.video import VideoModel
from app.model.job import JobModel, JobStatus
from datetime import datetime, UTC
from app.config.environments import RUNPOD_URL, RUNPOD_API_KEY, BACKEND_URL
from app.api.router_base import router_runpod as router
import requests

from app.utility.time import utc_now


class SummarizeRequest(BaseModel):
    video_id: int
    method: Literal["llm_only", "echofusion"]
    subtitle: bool
    vertical: bool


@router.post("/summarize")
async def summarize(request: Request, body: SummarizeRequest, db: AsyncSession = Depends(get_db)):
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

    if user.credit < 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credit"
        )

    result = await db.execute(
        select(VideoModel).where(VideoModel.id == body.video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    job = JobModel(
        user_id=user.id,
        video_id=video.id,
        method=body.method,
        status=JobStatus.PENDING,
        subtitle=body.subtitle,
        vertical=body.vertical,
        name="Pending Job"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        r = requests.post(
            url=f"{RUNPOD_URL}/run",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RUNPOD_API_KEY}"
            },
            json={
                "input": {
                    "webhook_url": f"{BACKEND_URL}/runpod/webhook/{job.id}",
                    "task": "process_video",
                    "video_url": video.file_path,
                    "options": {
                        "method": body.method,
                        "vertical": body.vertical,
                        "subtitles": body.subtitle,
                    }
                }
            },
            timeout=30
        )

        runpod_response = r.json()

        if "id" in runpod_response:
            job.runpod_job_id = runpod_response["id"]
            job.status = JobStatus.PROCESSING
            job.started_at = utc_now()
            job.name = f"Job {runpod_response['id'][:4]}"
            await db.commit()

        user.credit -= 1
        await db.commit()

        return {
            "job_id": job.id,
            "runpod_job_id": runpod_response.get("id"),
            "status": job.status,
            "message": "Job submitted successfully"
        }

    except requests.exceptions.RequestException as e:
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to submit job to RunPod: {str(e)}"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job to RunPod: {str(e)}"
        )