import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

def clean_and_convert_markdown_to_html(text: str) -> str:
    """
    Chuyển đổi Markdown cơ bản sang HTML tương thích với Telegram.
    Tự động escape các ký tự đặc biệt của HTML để tránh lỗi phân tích cú pháp.
    """
    import html
    import re

    if not text:
        return ""

    # 1. Escape các ký tự HTML đặc biệt để bảo vệ
    escaped_text = html.escape(text)

    # 2. Convert Headers (#, ##, ###) sang dạng chữ đậm
    lines = escaped_text.split("\n")
    for i, line in enumerate(lines):
        striped_line = line.strip()
        if striped_line.startswith("#"):
            indent = line[:len(line) - len(line.lstrip())]
            cleaned = striped_line.lstrip("#").strip()
            lines[i] = f"{indent}<b>{cleaned}</b>"
    escaped_text = "\n".join(lines)

    # 3. Convert **bold** sang <b>bold</b>
    escaped_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped_text)

    # 4. Convert *bold* sang <b>bold</b> (tránh bullet points)
    escaped_text = re.sub(r'(?<!\w)\*(?!\s)(.*?)(?<!\s)\*(?!\w)', r'<b>\1</b>', escaped_text)

    # 5. Convert _italic_ sang <i>italic</i>
    escaped_text = re.sub(r'(?<!\w)_(?!\s)(.*?)(?<!\s)_(?!\w)', r'<i>\1</i>', escaped_text)

    # 6. Convert `code` sang <code>code</code>
    escaped_text = re.sub(r'`(.*?)`', r'<code>\1</code>', escaped_text)

    return escaped_text

async def send_telegram_report(bot_token, message, chat_id, user_label="User", audio_path=None):
    print(f"[{user_label}] 📲 Đang gửi Telegram...")
    if not bot_token or not chat_id:
        print(f"[{user_label}] ⚠️ Không có Chat ID hoặc Token.")
        return

    bot = Bot(token=bot_token)

    # Tạo menu nút bấm
    keyboard = [
        [InlineKeyboardButton("📊 Sức khỏe & Đề xuất Tập", callback_data="daily")],
        [InlineKeyboardButton("💤 Phân tích Ngủ", callback_data="sleep_analysis"),
         InlineKeyboardButton("🏃 Phân tích Buổi tập", callback_data="workout")],
        [InlineKeyboardButton("🔋 Bắt mạch Năng lượng", callback_data="battery")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Convert markdown to robust HTML
    formatted_message = clean_and_convert_markdown_to_html(message)

    try:
        await bot.send_message(chat_id=chat_id, text=formatted_message, parse_mode='HTML', reply_markup=reply_markup)
        print(f"[{user_label}] ✅ Gửi thành công!")
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi HTML (Error: {e}), đang gửi Plain Text...")
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=None, reply_markup=reply_markup)
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
    formatted_alert = clean_and_convert_markdown_to_html(alert_text)

    try:
        await bot.send_message(chat_id=admin_id, text=formatted_alert, parse_mode='HTML')
        print("✅ Đã gửi Error Alert cho Admin.")
    except Exception as e:
        print(f"❌ Không thể gửi Error Alert: {e}")
        try:
             # Fallback plain text if HTML fails
            await bot.send_message(chat_id=admin_id, text=alert_text.replace('`', '').replace('*', ''), parse_mode=None)
        except:
            pass



async def send_progress_update(bot_token, message, chat_id, user_label="User"):
    if not bot_token or not chat_id: return
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi progress: {e}")
