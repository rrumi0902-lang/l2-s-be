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

# [최종 확정] TrimRange 모델: Pydantic v2 문법 및 유효성 검사 적용
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

class SummarizeRequest(BaseModel):
    video_id: int
    method: Literal["llm_only", "echofusion"]
    subtitle: bool
    subtitle_style: Optional[Literal["casual", "dynamic"]] = None
    vertical: bool
    crop_method: Optional[Literal["center", "fit"]] = None
    language: Optional[Literal["auto", "ko", "en", "es", "zh"]] = None
    target_duration: Optional[Union[Literal["auto"], int]] = "auto"
    trim_range: Optional[TrimRange] = None  # [추가됨]


@router.post("/summarize")
async def summarize(request: Request, body: SummarizeRequest, db: AsyncSession = Depends(get_db)):
    # ... (기존 인증, 세션, 유저 확인 로직 생략 - 그대로 유지) ...
    # session_token 확인 ~ video 조회까지 기존 코드 유지

    # ... (기본값 설정 로직 생략 - 그대로 유지) ...

    logger.info(f"Summarize request for video {body.video_id}: target_duration={body.target_duration}")

    # [최종 확정] RunPod 전송용 데이터 변환
    trim_options = body.trim_range.model_dump() if body.trim_range else None

    # Job 생성 로직
    job = JobModel(
        # ... 기존 필드들 ...
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

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                            "trim_range": trim_options,  # [추가됨]
                        }
                    }
                }
            )
            response.raise_for_status()
            runpod_response = response.json()

        # ... (이후 응답 처리 및 DB 업데이트 로직 생략 - 그대로 유지) ...
        # if "id" in runpod_response: ...
        
        return {
            "job_id": job.id,
            "runpod_job_id": runpod_response.get("id"),
            "status": job.status,
            "message": "Job submitted successfully"
        }

    except httpx.HTTPError as e:
        # ... (에러 처리 로직 생략 - 그대로 유지) ...
        raise HTTPException(...)