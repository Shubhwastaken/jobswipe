import os
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
STUDENT_EMAIL_DOMAIN = os.getenv("STUDENT_EMAIL_DOMAIN", "srmist.edu.in").lower()
ADMIN_EMAIL_DOMAIN = os.getenv("ADMIN_EMAIL_DOMAIN", "admin.com").lower()
ADMIN_LOGIN_PASSWORD = os.getenv("ADMIN_LOGIN_PASSWORD", "Test123")
TRIAL_LOGIN_PASSWORD = os.getenv("TRIAL_LOGIN_PASSWORD", "Test123")

# Access-token lifetime in hours. Tokens carry an `exp` claim so leaked
# tokens stop working after this window (no refresh flow yet).
JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "12"))

# Browser origins allowed to call the API. Comma-separated; defaults to the
# local Vite dev server. Set CORS_ORIGINS to the deployed frontend origin(s)
# in production — never use "*" together with credentialed requests.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))

if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Supabase URL/keys are missing in .env")
