from app.api.health import healthcheck
from app.api.video import upload_file, upload_youtube, detail, my, recent, download, delete
from app.api.auth import (register, login, logout, withdraw, me)
from app.api.credit import add, use
from app.api.admin import forceLogout


def add_router(application):
    application.include_router(healthcheck.router)

    application.include_router(upload_file.router)
    application.include_router(upload_youtube.router)
    application.include_router(detail.router)
    application.include_router(my.router)
    application.include_router(recent.router)
    application.include_router(download.router)
    application.include_router(delete.router)

    application.include_router(register.router)
    application.include_router(login.router)
    application.include_router(logout.router)
    application.include_router(me.router)
    application.include_router(withdraw.router)

    application.include_router(add.router)
    application.include_router(use.router)

    application.include_router(forceLogout.router)