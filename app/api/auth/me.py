from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, UTC
from app.model.user import UserModel
from app.model.session import SessionModel
from app.db.dependency import get_db
from app.api.router_base import router_auth as router
from app.utility.time import utc_now


@router.get("/me")
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Require login"
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

    return {
        "user": {
            "email": user.email,
            "username": user.username,
            "credit": user.credit,
        }
    }