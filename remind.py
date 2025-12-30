import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Import module lấy dữ liệu từ Notion
from notion_db import get_users_from_notion

# Load biến môi trường
load_dotenv()
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def send_reminder_to_user(user_config, bot):
    """Gửi tin nhắn nhắc nhở đồng bộ cho 1 user"""
    name = user_config.get('name', 'Bạn')
    chat_id = user_config.get('telegram_chat_id')
    
    if not chat_id:
        print(f"⚠️ {name}: Không có Chat ID, bỏ qua.")
        return

    try:
        message = (
            f"🔔 *NHẮC NHỞ QUAN TRỌNG CHO {name.upper()}*\n\n"
            "Đã 4:00 PM rồi! 🕓\n"
            "Hãy mở App Garmin Connect và **đồng bộ dữ liệu ngay** "
            "để AI Coach có dữ liệu mới nhất phân tích vào lúc 5:00 PM nhé! ⌚️🏃‍♂️"
        )
        # Gửi tin nhắn
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"✅ Đã gửi nhắc nhở cho: {name}")
        
    except Exception as e:
        print(f"❌ Lỗi gửi cho {name}: {e}")

async def main():
    print("=== DAILY REMINDER (NOTION EDITION) ===")
    
    if not TELE_TOKEN:
        print("❌ Lỗi: Thiếu TELEGRAM_TOKEN trong file .env")
        return

    # 1. Lấy danh sách user từ Notion (đã lọc Active=True)
    users = get_users_from_notion()
    
    if not users:
        print("⚠️ Không tìm thấy user nào Active để nhắc nhở.")
        return

    print(f"🚀 Bắt đầu gửi nhắc nhở cho {len(users)} người dùng...")

    bot = Bot(token=TELE_TOKEN)
    
    # 2. Tạo task gửi song song (để chạy nhanh hơn)
    tasks = [send_reminder_to_user(user, bot) for user in users]
    await asyncio.gather(*tasks)
    
    print("\n=== ĐÃ HOÀN TẤT GỬI NHẮC NHỞ ===")

if __name__ == "__main__":
    asyncio.run(main())