"""
Supabase Client: Database connection and operations.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def get_client(use_service_key=False) -> "Client":
    """
    Get Supabase client.
    use_service_key=True for backend writes (model results).
    use_service_key=False for frontend reads (anon key).
    """
    if not HAS_SUPABASE:
        raise ImportError(
            "supabase-py is required. Install with: pip install supabase"
        )

    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL not set in .env")

    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_ANON_KEY
    if not key:
        raise ValueError(
            f"{'SUPABASE_SERVICE_KEY' if use_service_key else 'SUPABASE_ANON_KEY'} not set in .env"
        )

    return create_client(SUPABASE_URL, key)


def test_connection():
    """Test database connection."""
    try:
        client = get_client()
        print(f"✅ Connected to Supabase: {SUPABASE_URL}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
