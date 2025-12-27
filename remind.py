import os
import json
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def send_reminder_to_user(user_config, bot):
    name = user_config.get('name', 'Bạn')
    chat_id = user_config.get('telegram_chat_id') # Lưu ý key này phải khớp với trong USERS_JSON của bạn
    
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
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"✅ Đã nhắc {name}")
    except Exception as e:
        print(f"❌ Lỗi nhắc {name}: {e}")

async def main():
    print("=== DAILY REMINDER ===")
    
    if not TELE_TOKEN:
        print("❌ Thiếu TELEGRAM_TOKEN")
        return

    # Lấy danh sách user từ biến môi trường (Giống main.py)
    users_json = os.getenv("USERS_JSON")
    if not users_json:
        print("❌ Không tìm thấy USERS_JSON")
        return
        
    try:
        users = json.loads(users_json)
    except:
        print("❌ Lỗi format JSON user")
        return

    bot = Bot(token=TELE_TOKEN)
    
    # Gửi tin nhắn song song cho mọi user
    tasks = [send_reminder_to_user(user, bot) for user in users]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())