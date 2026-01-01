import os
import asyncio
import argparse
from dotenv import load_dotenv

# Import từ App packages
from app.services.notion_service import get_users_from_notion
from app.services.telegram_service import send_reminder_message

# Load biến môi trường
load_dotenv()
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def main():
    parser = argparse.ArgumentParser(description="Gửi nhắc nhở Telegram")
    parser.add_argument("--type", default="daily", help="Loại nhắc nhở: daily (chiều) hoặc sleep (sáng)")
    args = parser.parse_args()
    
    reminder_type = args.type
    print(f"=== REMINDER SERVICE: {reminder_type.upper()} ===")
    
    if not TELE_TOKEN:
        print("❌ Lỗi: Thiếu TELEGRAM_TOKEN trong file .env")
        return

    # 1. Lấy danh sách user từ Notion (đã lọc Active=True)
    users = get_users_from_notion()
    
    if not users:
        print("⚠️ Không tìm thấy user nào Active để nhắc nhở.")
        return

    print(f"🚀 Bắt đầu gửi nhắc nhở cho {len(users)} người dùng...")

    # 2. Gửi nhắc nhở
    # Lưu ý: send_reminder_message cần TELE_TOKEN để khởi tạo Bot bên trong, hoặc Bot object.
    # Logic cũ khởi tạo Bot ở main và pass vào.
    # Logic mới trong telegram_service: send_reminder_message(bot_token, user_config, type)
    
    tasks = [send_reminder_message(TELE_TOKEN, user, reminder_type) for user in users]
    await asyncio.gather(*tasks)
    
    print("\n=== ĐÃ HOÀN TẤT GỬI NHẮC NHỞ ===")

if __name__ == "__main__":
    asyncio.run(main())