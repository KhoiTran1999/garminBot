
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    NOTION_PROMPT_DATABASE_ID = os.getenv("NOTION_PROMPT_DATABASE_ID")
    TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
    REDIS_URL = os.getenv("REDIS_URL")

    # Load 9Router Key (không fallback về GEMINI_API_KEY)
    ROUTER9_API_KEY = os.getenv("ROUTER9_API_KEY")
    ROUTER9_COMBOS_MODEL = os.getenv("ROUTER9_COMBOS_MODEL")

    if not ROUTER9_API_KEY:
        print("WARNING: ROUTER9_API_KEY not found in .env! AI report will not work.")

    # Load danh sách Gemini Keys (dành cho TTS)
    GEMINI_API_KEYS = []
    _main_gemini_key = os.getenv("GEMINI_API_KEY")
    if _main_gemini_key:
        GEMINI_API_KEYS.append(_main_gemini_key)

    _j = 1
    while True:
        _key = os.getenv(f"GEMINI_API_KEY_{_j}")
        if _key:
            GEMINI_API_KEYS.append(_key)
            _j += 1
        else:
            break

    if not GEMINI_API_KEYS:
        print("WARNING: GEMINI_API_KEY not found in .env! TTS features will not work.")
