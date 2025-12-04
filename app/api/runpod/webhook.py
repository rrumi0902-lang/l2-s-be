from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.job import JobModel, JobStatus
from datetime import datetime, UTC
from app.api.router_base import router_runpod as router


@router.post("/webhook/{job_id}")
async def runpod_webhook(job_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Webhook endpoint for RunPod to notify us when a job is completed or failed
    This endpoint does NOT require authentication as it's called by RunPod
    """
    try:
        payload = await request.json()

        assigned_job_id = payload.get("job_id")
        status = payload.get("status")  # "completed" or "failed"
        result_url = payload.get("result_url")
        error = payload.get("error")

        if not job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing job_id in webhook payload"
            )

        # Find job in database
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Update job status
        if status == "completed":
            job.status = JobStatus.COMPLETED
            job.result_url = result_url
            job.completed_at = datetime.now(UTC)
        elif status == "failed":
            job.status = JobStatus.FAILED
            job.error_message = error
            job.completed_at = datetime.now(UTC)
        else:
            # Unknown status, log it but don't fail
            job.error_message = f"Unknown status from webhook: {status}"

        db.commit()

        return {
            "message": "Webhook received successfully",
            "job_id": job_id,
            "status": job.status
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )
