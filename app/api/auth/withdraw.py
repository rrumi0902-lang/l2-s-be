from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import UserModel
from app.config.environments import ENVIRONMENT

COOKIE_SECURE = False
COOKIE_SAMESITE = "lax"
if ENVIRONMENT == "production":
    COOKIE_SECURE = True
    COOKIE_SAMESITE = "none"

router = APIRouter(
    prefix="/auth",
    tags=["Auth"])


@router.delete("/withdraw")
async def withdraw(request: Request, response: Response, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in"
        )

    session = (
        db.query(SessionModel)
        .filter(SessionModel.session_token == session_token)
        .first()
    )

    if not session or (session.expires_at and session.expires_at < datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )

    db.query(UserModel).filter(UserModel.id == session.user_id).delete()
    db.query(SessionModel).filter(SessionModel.session_token == session_token).delete()
    db.commit()

    response.delete_cookie(
        "session_token",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )

    return {"message": "Account has been successfully deleted"}