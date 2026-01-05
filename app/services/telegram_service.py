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

async def send_error_alert(bot_token, admin_id, error_message):
    """
    Gửi cảnh báo lỗi nghiêm trọng đến Admin Telegram.
    """
    if not bot_token or not admin_id:
        print("⚠️ Không có Token hoặc Admin ID để gửi alert.")
        return

    bot = Bot(token=bot_token)
    alert_text = f"🚨 **CRASH ALERT** 🚨\n\nBot đã gặp lỗi nghiêm trọng:\n\n`{error_message}`"
    
    try:
        await bot.send_message(chat_id=admin_id, text=alert_text, parse_mode='Markdown')
        print("✅ Đã gửi Error Alert cho Admin.")
    except Exception as e:
        print(f"❌ Không thể gửi Error Alert: {e}")
        try:
             # Fallback plain text if markdown fails
            await bot.send_message(chat_id=admin_id, text=alert_text.replace('`', '').replace('*', ''), parse_mode=None)
        except:
            pass


