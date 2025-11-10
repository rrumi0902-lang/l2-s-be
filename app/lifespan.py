from fastapi import FastAPI
from app.db.initialize import initialize_db
from contextlib import asynccontextmanager
from app.service.sessionCleaner import start_cleanup_thread


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup logic
    print("App starting up...")
    initialize_db()
    start_cleanup_thread()
    yield
    # Shutdown logic
    print("App shutting down...")