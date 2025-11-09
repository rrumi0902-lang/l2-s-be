from fastapi import APIRouter, Request, Response, HTTPException, status
from pydantic import BaseModel
from app.db.fakedb import fakedb

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
        data: LoginRequest
):
    email = data.email
    password = data.password

    user = fakedb.get(email)
    if not user or user.password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Id or password is not correct"
        )

    request.session["user"] = email

    return {
        "message": "Successfully logged in",
        "username": user.username
    }
