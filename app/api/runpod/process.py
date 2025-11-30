from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from datetime import datetime, UTC
from app.config.environments import RUNPOD_URL, RUNPOD_API_KEY
import requests
from app.api.router_base import router_runpod as router


class OptionsModel(BaseModel):
    language: str
    method: Literal["llm_only", "echofusion"]

class InputModel(BaseModel):
    job_id: str | None = None
    task: Literal["process_video", "generate_thumbnail"]
    video_url: str
    options: OptionsModel


class DataModel(BaseModel):
    input: InputModel


class RunpodRequest(BaseModel):
    command: str
    data: DataModel | None = None


@router.post("/process")
async def process(request: Request, body: RunpodRequest, db: Session = Depends(get_db)):
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
    
    r = requests.post(
        url=f"{RUNPOD_URL}/{body.command}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RUNPOD_API_KEY}"
        },
        json=body.data.model_dump() if body.data else {},
    )
    
    return r.json()