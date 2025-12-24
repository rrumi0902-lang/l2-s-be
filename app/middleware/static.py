from fastapi.staticfiles import StaticFiles
import os


def add_static_file_serving(application):
    """
    Mount static file serving for uploads directory.
    Skips mounting if directory doesn't exist (e.g., in serverless environments like Vercel).
    """
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

    # Only mount if directory exists (skip in serverless environments)
    if os.path.exists(UPLOAD_DIR) and os.path.isdir(UPLOAD_DIR):
        application.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
    else:
        # Create directory in local development if it doesn't exist
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            application.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
        except (OSError, PermissionError):
            # Skip mounting in read-only environments (e.g., Vercel)
            pass
