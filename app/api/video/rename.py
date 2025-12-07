from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.video import VideoModel
from app.model.user import UserModel
from app.utility.time import utc_now
from app.api.router_base import router_video as router


class RenameRequest(BaseModel):
    video_id: str
    name: str


@router.patch("/rename")
async def rename(request: Request, data: RenameRequest, db: AsyncSession = Depends(get_db)):
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

    result = await db.execute(
        select(VideoModel).where(VideoModel.id == int(data.video_id))
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    video.name = data.name
    await db.commit()
    await db.refresh(video)

    return {"message": f"Video renamed to {video.name}"}