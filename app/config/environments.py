import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SESSION_EXPIRE_TIME = 60 * 60 * 6  # 6 Hour
DEFAULT_PORT = 8080
DEFAULT_ENVIRONMENT = "development"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is missing! Set it in your .env file.")

SESSION_EXPIRE_TIME = int(os.getenv("SESSION_EXPIRE_TIME", DEFAULT_SESSION_EXPIRE_TIME))
PORT = int(os.getenv("PORT", DEFAULT_PORT))
ENVIRONMENT = os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT)
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not all([SUPABASE_DB_URL, SUPABASE_PROJECT_URL, SUPABASE_SERVICE_KEY]):
    raise RuntimeError("SUPABASE related environment variable is missing! Set it in your .env file.")

RUNPOD_URL = os.getenv("RUNPOD_URL")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
if not all([RUNPOD_URL, RUNPOD_API_KEY]):
    raise RuntimeError("RUNPOD related environment variable is missing! Set it in your .env file.")

BACKEND_URL = os.getenv("BACKEND_URL")
if not BACKEND_URL:
    raise RuntimeError("No backend url")
