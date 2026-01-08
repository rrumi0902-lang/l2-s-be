from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel, field_validator, model_validator
from typing import Literal, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.model.video import VideoModel
from app.model.job import JobModel, JobStatus
from app.config.environments import RUNPOD_URL, RUNPOD_API_KEY, BACKEND_URL
from app.api.router_base import router_runpod as router
import httpx
import logging
from app.utility.time import utc_now

logger = logging.getLogger(__name__)

# [TrimRange 모델 정의]
class TrimRange(BaseModel):
    start: float
    end: float

    @field_validator('start', 'end')
    @classmethod
    def must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError('timestamp must be non-negative')
        return v

    @model_validator(mode='after')
    def end_must_be_after_start(self) -> 'TrimRange':
        if self.end <= self.start:
            raise ValueError('end must be greater than start')
        return self

# [SummarizeRequest 모델 정의]
class SummarizeRequest(BaseModel):
    video_id: int
    method: Literal["llm_only", "echofusion"]
    subtitle: bool
    subtitle_style: Optional[Literal["casual", "dynamic"]] = None
    vertical: bool
    crop_method: Optional[Literal["center", "fit"]] = None
    language: Optional[Literal["auto", "ko", "en", "es", "zh"]] = None
    target_duration: Optional[Union[Literal["auto"], int]] = "auto"
    trim_range: Optional[TrimRange] = None


@router.post("/summarize")
async def summarize(request: Request, body: SummarizeRequest, db: AsyncSession = Depends(get_db)):
    # 1. 세션 확인
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

    # 2. 유저 확인
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

    # 3. 비디오 확인
    result = await db.execute(
        select(VideoModel).where(VideoModel.id == body.video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # 기본값 설정
    if body.subtitle_style is None:
        body.subtitle_style = "dynamic"
    if body.crop_method is None:
        body.crop_method = "center"

    logger.info(f"Summarize request for video {body.video_id}: target_duration={body.target_duration}")

    # 4. Trim 옵션 준비
    trim_options = body.trim_range.model_dump() if body.trim_range else None

    # 5. Job 생성
    job = JobModel(
        user_id=user.id,
        video_id=video.id,
        method=body.method,
        status=JobStatus.PENDING,
        subtitle=body.subtitle,
        subtitle_style=body.subtitle_style,
        vertical=body.vertical,
        crop_method=body.crop_method,
        language=body.language,
        name="Pending Job"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 6. RunPod 요청 전송
    try:
        # 타임아웃을 120초로 설정 (Cold Start 대비)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url=f"{RUNPOD_URL}/run",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {RUNPOD_API_KEY}"
                },
                json={
                    "input": {
                        "job_id": str(job.id),
                        "webhook_url": f"{BACKEND_URL}/runpod/webhook/{job.id}",
                        "task": "process_video",
                        "video_url": video.file_path,
                        "options": {
                            "method": body.method,
                            "subtitles": body.subtitle,
                            "subtitle_style": body.subtitle_style,
                            "vertical": body.vertical,
                            "crop_method": body.crop_method,
                            "language": body.language,
                            "target_duration": body.target_duration,
                            "trim_range": trim_options,  # Trim 옵션 전달
                        }
                    }
                }
            )
            response.raise_for_status()
            runpod_response = response.json()

        if "id" in runpod_response:
            job.runpod_job_id = runpod_response["id"]
            job.status = JobStatus.PROCESSING
            job.started_at = utc_now()
            job.name = f"Job {runpod_response['id'][:4]}"
            await db.commit()

        # 크레딧 차감
        user.credit -= 1
        await db.commit()

        return {
            "job_id": job.id,
            "runpod_job_id": runpod_response.get("id"),
            "status": job.status,
            "message": "Job submitted successfully"
        }

    except httpx.HTTPError as e:
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to submit job to RunPod: {str(e)}"
        await db.commit()

        logger.error(f"RunPod submission failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job to RunPod: {str(e)}"
        )