import uuid
from datetime import datetime, UTC, timedelta
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel
from app.model.user import UserModel
from app.model.session import SessionModel
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.config.environments import SESSION_EXPIRE_TIME

router = APIRouter(
    prefix="/auth",
    tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if not user or user.password != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Id or password is not correct"
        )

    session_token = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(minutes=SESSION_EXPIRE_TIME)

    session = SessionModel(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=SESSION_EXPIRE_TIME,
        secure=False, #NO HTTPS TIL DOMAIN BUY
        samesite="lax"
    )

    return {"message": "Successfully logged in"}