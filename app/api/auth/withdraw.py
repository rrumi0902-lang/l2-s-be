from fastapi import Request, Response, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, UTC
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.config.environments import ENVIRONMENT
from app.api.router_base import router_auth as router
from app.utility.time import utc_now

COOKIE_SECURE = False
COOKIE_SAMESITE = "lax"
if ENVIRONMENT == "production":
    COOKIE_SECURE = True
    COOKIE_SAMESITE = "none"


@router.delete("/withdraw")
async def withdraw(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in"
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

    await db.execute(delete(SessionModel).where(SessionModel.session_token == session_token))
    await db.execute(delete(UserModel).where(UserModel.id == session.user_id))
    await db.commit()

    response.delete_cookie(
        "session_token",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )

    return {"message": "Account has been successfully deleted"}