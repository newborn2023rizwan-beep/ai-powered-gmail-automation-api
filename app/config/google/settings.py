import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

if not GOOGLE_CLIENT_ID:
    raise ValueError("GOOGLE_CLIENT_ID is missing")

if not GOOGLE_CLIENT_SECRET:
    raise ValueError("GOOGLE_CLIENT_SECRET is missing")