import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SESSION_EXPIRE_TIME = 60 * 60 * 6  # 6 Hour
DEFAULT_PORT = 8000

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is missing! Set it in your .env file.")

SESSION_EXPIRE_TIME = int(os.getenv("SESSION_EXPIRE", DEFAULT_SESSION_EXPIRE_TIME))
PORT = int(os.getenv("PORT", DEFAULT_PORT))
