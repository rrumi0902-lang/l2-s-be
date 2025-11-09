import uvicorn
from app.application import application
from app.config.environments import PORT

if __name__ == "__main__":
    uvicorn.run(
        application,
        host="0.0.0.0",
        port=PORT,
        reload=False
    )
