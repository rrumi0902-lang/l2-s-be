from fastapi import FastAPI
from app.middleware.cors import add_cors
from app.middleware.session import add_session
from app.middleware.static import add_static_file_serving
from app.api.router import add_router

application = FastAPI(
    title="SVSP FastAPI Service",
    description="Semantic Video Summarization Pipeline Backend API documentation",
    version="1.0.0"
)

add_cors(application)
add_session(application)
add_static_file_serving(application)
add_router(application)
