import os
from telegram import Bot

async def send_telegram_report(bot_token, message, chat_id, user_label="User", audio_path=None):
    print(f"[{user_label}] 📲 Đang gửi Telegram...")
    if not bot_token or not chat_id:
        print(f"[{user_label}] ⚠️ Không có Chat ID hoặc Token.")
        return

    bot = Bot(token=bot_token)
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"[{user_label}] ✅ Gửi thành công!")
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi Markdown, đang gửi Plain Text...")
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
        except Exception as e2:
            print(f"❌ Lỗi gửi tin nhắn: {e2}")

    # Gửi Voice nếu có
    if audio_path and os.path.exists(audio_path):
        print(f"[{user_label}] 🎙️ Đang gửi Voice Note...")
        try:
            with open(audio_path, 'rb') as audio:
                await bot.send_voice(chat_id=chat_id, voice=audio, caption="🎧 Voice Coach")
            print(f"[{user_label}] ✅ Gửi Voice thành công!")
        except Exception as e:
            print(f"[{user_label}] ⚠️ Lỗi gửi Voice: {e}")

async def send_reminder_message(bot_token, user_config, reminder_type="daily"):
    """Gửi tin nhắn nhắc nhở đồng bộ cho 1 user"""
    name = user_config.get('name', 'Bạn')
    chat_id = user_config.get('telegram_chat_id')
    
    if not chat_id:
        print(f"⚠️ {name}: Không có Chat ID, bỏ qua.")
        return

    bot = Bot(token=bot_token)
    
    try:
        if reminder_type == "sleep":
            message = (
                f"☀️ *CHÀO BUỔI SÁNG, {name.upper()}!* \n\n"
                "Đã 7:00 AM! 🕖\n"
                "Hãy mở App Garmin Connect và **đồng bộ dữ liệu giấc ngủ** "
                "để AI Coach phân tích vào lúc 7:30 AM nhé! 🛌💤"
            )
        else:
            # Default Daily Reminder (4PM)
            message = (
                f"🔔 *NHẮC NHỞ QUAN TRỌNG CHO {name.upper()}*\n\n"
                "Đã 4:00 PM rồi! 🕓\n"
                "Hãy mở App Garmin Connect và **đồng bộ dữ liệu ngay** "
                "để AI Coach có dữ liệu mới nhất phân tích vào lúc 5:00 PM nhé! ⌚️🏃‍♂️"
            )

        # Gửi tin nhắn
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"✅ Đã gửi nhắc nhở ({reminder_type}) cho: {name}")
        
    except Exception as e:
        print(f"❌ Lỗi gửi cho {name}: {e}")
