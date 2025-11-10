from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.model.session import SessionModel

router = APIRouter(
    prefix="/auth",
    tags=["Auth"])


@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in"
        )

    db.query(SessionModel).filter(SessionModel.session_token == session_token).delete()
    db.commit()

    response.delete_cookie("session_token")
    return {"message": "Successfully logged out"}