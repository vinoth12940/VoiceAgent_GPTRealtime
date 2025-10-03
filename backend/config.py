import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- OpenAI Realtime / Server ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
APP_ORIGIN = os.getenv("APP_ORIGIN", "http://127.0.0.1:8000")

DB_PATH = os.getenv("DB_PATH", "policies.db")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me")

# Realtime config - Aligned with latest OpenAI documentation (Aug 28, 2025)
REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-realtime")
REALTIME_VOICE = os.getenv("REALTIME_VOICE", "shimmer")  # More natural, professional voice
REALTIME_SESSIONS_URL = "https://api.openai.com/v1/realtime/sessions"
