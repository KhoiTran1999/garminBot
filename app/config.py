
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

    # Load danh sách Gemini Keys
    ROUTER9_API_KEYS = []
    _main_key = os.getenv("ROUTER9_API_KEY")
    if _main_key:
        ROUTER9_API_KEYS.append(_main_key)
    
    # Load các key phụ (GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...)
    _i = 1
    while True:
        _key = os.getenv(f"ROUTER9_API_KEY_{_i}")
        if _key:
            ROUTER9_API_KEYS.append(_key)
            _i += 1
        else:
            break
            
    if not ROUTER9_API_KEYS:
        print("⚠️ CẢNH BÁO: Không tìm thấy ROUTER9_API_KEY nào trong .env!")
