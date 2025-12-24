from fastapi import FastAPI
from app.db.database import Base, engine
from contextlib import asynccontextmanager
from app.service.sessionCleaner import start_cleanup_task


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup logic
    print("App starting up...")

# async with engine.begin() as conn:
 #       await conn.run_sync(Base.metadata.create_all)

    start_cleanup_task()
    yield
    # Shutdown logic
    print("App shutting down...")