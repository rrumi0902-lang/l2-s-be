from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean
from datetime import datetime, UTC
from app.db.database import Base
import enum


class JobStatus(str, enum.Enum):
    """Job processing status enumeration"""
    PENDING = "pending"  # Job created, not started
    PROCESSING = "processing"  # Job is being processed
    COMPLETED = "completed"  # Job completed successfully
    FAILED = "failed"  # Job failed with error


class JobModel(Base):
    """Model for tracking video processing jobs"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    method = Column(String, nullable=True)  # "llm_only" or "echofusion"
    subtitle = Column(Boolean, nullable=False, default=False)
    vertical = Column(Boolean, nullable=False, default=False)
    result_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    runpod_job_id = Column(String, nullable=True)  # RunPod's internal job ID
    name = Column(String, nullable=False)
