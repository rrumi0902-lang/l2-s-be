import asyncio
from datetime import datetime, UTC
from sqlalchemy import delete
from app.db.database import AsyncSessionLocal
from app.model.session import SessionModel
from app.config.environments import SESSION_EXPIRE_TIME
from app.utility.time import utc_now

SESSION_CLEANER_INTERVAL = SESSION_EXPIRE_TIME


async def cleanup_expired_sessions():
    async with AsyncSessionLocal() as db:
        now = utc_now()
        result = await db.execute(
            delete(SessionModel).where(
                SessionModel.expires_at != None,
                SessionModel.expires_at < now
            )
        )
        await db.commit()
        return result.rowcount


async def session_cleanup_worker():
    while True:
        try:
            deleted = await cleanup_expired_sessions()
            if deleted > 0:
                print(f"[SessionCleaner] Deleted {deleted} expired sessions")
        except Exception as e:
            print(f"[SessionCleaner] Error: {e}")

        await asyncio.sleep(SESSION_CLEANER_INTERVAL)


def start_cleanup_task():
    asyncio.create_task(session_cleanup_worker())
    print("[SessionCleaner] Background cleanup task started.")