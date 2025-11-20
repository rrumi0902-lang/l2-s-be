from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from app.model.user import UserModel
from app.model.session import SessionModel
from app.db.dependency import get_db

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.get("/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Require login"
        )

    session = (
        db.query(SessionModel)
        .filter(SessionModel.session_token == session_token)
        .first()
    )

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

    return {
        "user": {
            "email": user.email,
            "username": user.username,
            "credit": user.credit,
        }
    }
