from fastapi import APIRouter, Request

router = APIRouter(
    prefix="/auth",
    tags=["Auth"])


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}
