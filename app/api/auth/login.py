import uuid
from datetime import datetime, UTC, timedelta
from fastapi import Request, Response, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.model.user import UserModel
from app.model.session import SessionModel
from app.db.dependency import get_db
from app.config.environments import SESSION_EXPIRE_TIME, ENVIRONMENT
from app.utility.security import verify_password
from app.api.router_base import router_auth as router
from app.utility.time import utc_now

COOKIE_SECURE = False
COOKIE_SAMESITE = "lax"
if ENVIRONMENT == "production":
    COOKIE_SECURE = True
    COOKIE_SAMESITE = "none"


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(
        request: Request,
        response: Response,
        data: LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UserModel).where(UserModel.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Id or password is not correct"
        )

    await db.execute(delete(SessionModel).where(SessionModel.user_id == user.id))
    await db.commit()

    session_token = str(uuid.uuid4())
    expires_at = utc_now() + timedelta(seconds=SESSION_EXPIRE_TIME)

    session = SessionModel(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(session)
    await db.commit()

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=SESSION_EXPIRE_TIME,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )

    return {"message": "Successfully logged in"}