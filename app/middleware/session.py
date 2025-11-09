from starlette.middleware.sessions import SessionMiddleware
from app.config.environments import SECRET_KEY, SESSION_EXPIRE_TIME


def add_session(application):
    application.add_middleware(SessionMiddleware,
                               secret_key=SECRET_KEY,
                               max_age=SESSION_EXPIRE_TIME)
