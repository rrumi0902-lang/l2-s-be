from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.db.fakedb import fakedb
from app.model.user import UserModel

router = APIRouter(
    prefix="/auth",
    tags=["Auth"])


class RegisterModel(BaseModel):
    email: str
    username: str
    password: str


@router.post("/register")
async def register(data: RegisterModel):
    if data.username in fakedb:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exist"
        )
    fakedb[data.email] = UserModel(email=data.email,
                                   username=data.username,
                                   password=data.password)
    return {"message": "Successfully registered", "user": data.username}
