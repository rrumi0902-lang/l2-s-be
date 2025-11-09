from fastapi.staticfiles import StaticFiles
import os


def add_static_file_serving(application):
    BASE_DIR = (
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )
    )
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    application.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
