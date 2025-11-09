from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get(
    "/alive",
    summary="Health Check",
    description="Return data about whether server is live",
    responses={
        200: {
            "description": "When server is alive",
            "content": {
                "application/json": {
                    "example": {"message": "yes"}
                }
            }
        }
    }
)
async def healthcheck():
    return {"message": "yes"}
