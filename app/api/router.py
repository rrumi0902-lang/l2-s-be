from app.api.health import healthcheck
from app.api.video import upload
from app.api.auth import (register, login, logout, withdraw, me)
from app.api.credit import add, use
from app.api.admin import forceLogout


def add_router(application):
    application.include_router(healthcheck.router)
    application.include_router(upload.router)

    application.include_router(register.router)
    application.include_router(login.router)
    application.include_router(logout.router)
    application.include_router(me.router)
    application.include_router(withdraw.router)

    application.include_router(add.router)
    application.include_router(use.router)

    application.include_router(forceLogout.router)