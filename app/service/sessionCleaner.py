import time, threading
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.model.session import SessionModel
from app.config.environments import SESSION_EXPIRE_TIME


def cleanup_expired_sessions(db: Session):
    now = datetime.now(UTC)
    expired_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.expires_at != None)
        .filter(SessionModel.expires_at < now)
    )
    count = expired_sessions.count()
    expired_sessions.delete()
    db.commit()
    return count


SESSION_CLEANER_INTERVAL = SESSION_EXPIRE_TIME


def session_cleanup_worker():
    """
    Background worker that cleans up expired sessions.
    Creates a fresh database connection for each iteration to avoid timeout issues.
    """
    while True:
        db = None
        try:
            # Create a fresh database connection for each iteration
            db = SessionLocal()
            deleted = cleanup_expired_sessions(db)
            if deleted > 0:
                print(f"[SessionCleaner] Deleted {deleted} expired sessions")
        except Exception as e:
            print(f"[SessionCleaner] Error: {e}")
        finally:
            # Always close the connection, even if db is None
            if db is not None:
                try:
                    db.close()
                except Exception as close_error:
                    print(f"[SessionCleaner] Error closing connection: {close_error}")

        # Sleep before next cleanup cycle
        time.sleep(SESSION_CLEANER_INTERVAL)


def start_cleanup_thread():
    thread = threading.Thread(target=session_cleanup_worker, daemon=True)
    thread.start()
    print("[SessionCleaner] Background cleanup thread started.")