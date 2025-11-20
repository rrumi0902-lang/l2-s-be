from datetime import datetime, UTC
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel
from app.model.user import  UserModel
from pydantic import BaseModel

router = APIRouter(
    prefix="/credit",
    tags=["Credit"])


class CreditAddRequest(BaseModel):
    amount: int


@router.post("/use")
async def add(request: Request, data: CreditAddRequest, db: Session = Depends(get_db)):
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

    user.credit -= data.amount
    db.commit()
    db.refresh(user)

    return {"message": f"{data.amount} credit has been used.", "total_credit": user.credit}