from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.job import JobModel, JobStatus
from app.model.user import UserModel
from datetime import datetime, UTC
from app.api.router_base import router_runpod as router
import logging

logger = logging.getLogger(__name__)


@router.post("/webhook/{job_id}")
async def runpod_webhook(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    RunPod Webhook Handler - Improved Version

    Expected Payload from RunPod:
    {
        "status": "completed" | "failed" | "partial",
        "result_url": "https://...",
        "error": "error message",
        "processing_method": "multimodal" | "visual_only" | "text_only",
        "message": "detailed message",
        "metadata": {...}
    }
    """
    try:
        payload = await request.json()

        # Basic fields
        webhook_status = payload.get("status")
        result_url = payload.get("result_url")
        error = payload.get("error")

        # Enhanced fields (sent from RunPod handler.py)
        processing_method = payload.get("processing_method", "unknown")
        detail_message = payload.get("message", "")
        metadata = payload.get("metadata", {})

        # New fields for subtitle-aware message logic
        has_subtitles = payload.get("has_subtitles", False)
        detected_language = payload.get("language", None)

        if not job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing job_id in webhook payload"
            )

        # Find job
        result = await db.execute(
            select(JobModel).where(JobModel.id == int(job_id))
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        logger.info(f"Webhook received for job {job_id}: status={webhook_status}, method={processing_method}, has_subtitles={has_subtitles}")

        # Process by status
        if webhook_status == "completed":
            job.status = JobStatus.COMPLETED
            job.result_url = result_url
            job.completed_at = datetime.now(UTC)

            # Message priority: has_subtitles > processing_method
            # If subtitles exist, show clean success message (ignore "no speech detected")
            if has_subtitles:
                lang_display = detected_language if detected_language and detected_language != "auto" else "detected"
                job.error_message = f"[OK] Completed with subtitles ({lang_display})"
                logger.info(f"Job {job_id} completed with subtitles (lang: {lang_display})")
            elif processing_method == "visual_only":
                # Only show "no speech detected" when no subtitles were generated
                job.error_message = "[OK] Visual features only - no speech detected"
                logger.info(f"Job {job_id} completed with visual-only processing (no subtitles)")
            elif processing_method == "text_only":
                job.error_message = "[OK] Completed (Text analysis only)"
            elif processing_method == "multimodal":
                job.error_message = None  # Normal completion, no error
                logger.info(f"Job {job_id} completed with multimodal fusion")
            else:
                # Default case - use detail_message if available
                job.error_message = detail_message if detail_message else None

        elif webhook_status == "partial":
            # Partial success (e.g., TXT failed but HD succeeded)
            job.status = JobStatus.COMPLETED
            job.result_url = result_url
            job.completed_at = datetime.now(UTC)

            warning_msg = f"[WARN] Partial success: {detail_message or 'Fallback to visual features'}"
            job.error_message = warning_msg
            logger.warning(f"Job {job_id} completed partially: {warning_msg}")

        elif webhook_status == "failed":
            job.status = JobStatus.FAILED
            job.error_message = error or "Unknown processing error"
            job.completed_at = datetime.now(UTC)

            # Refund credit on failure
            result = await db.execute(
                select(UserModel).where(UserModel.id == job.user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.credit += 1
                logger.info(f"Refunded 1 credit to user {user.id} for failed job {job_id}")

        else:
            # Unknown status
            job.error_message = f"Unknown webhook status: {webhook_status}"
            logger.error(f"Unknown webhook status for job {job_id}: {webhook_status}")

        await db.commit()

        return {
            "message": "Webhook processed successfully",
            "job_id": job_id,
            "status": job.status,
            "processing_method": processing_method,
            "has_subtitles": has_subtitles,
            "result_url": result_url
        }

    except ValueError as e:
        # Job ID conversion failure
        logger.error(f"Invalid job_id format: {job_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job_id: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Webhook processing error for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )