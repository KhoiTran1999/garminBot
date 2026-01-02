import os
import asyncio
import argparse
from datetime import date
from dotenv import load_dotenv
from garminconnect import Garmin

# Import Services
from app.services.notion_service import get_users_from_notion
from app.services.garmin_service import get_processed_data
from app.services.ai_service import get_ai_advice, get_speech_script, generate_audio_from_text
from app.services.telegram_service import send_telegram_report

# --- CẤU HÌNH CHUNG ---
load_dotenv()
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def process_single_user(user_config, mode):
    # Lấy thông tin từ object user của Notion
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')
    tele_id = user_config.get('telegram_chat_id')

    if not email or not password: 
        print(f"[{name}] ❌ Thiếu Email/Pass, bỏ qua.")
        return

    try:
        client = Garmin(email, password)
        client.login()
        print(f"[{name}] ✅ Đăng nhập Garmin thành công.")
        
        today = date.today()
        # today = date(2025, 12, 30) # Dùng khi test ngày cũ

        # 1. Lấy dữ liệu Garmin (Sleep + Stats)
        r_data, r_score, l_data = get_processed_data(client, today, name)

        print("r_data", r_data)
        print("r_score", r_score)
        print("l_data", l_data)
        return
        # 2. Gọi AI (Truyền cả user_config chứa Goal/Injury từ Notion)
        ai_report = get_ai_advice(GEMINI_API_KEY, today, r_data, r_score, l_data, user_config, mode)

        # 3. Tạo Voice Script & Audio
        speech_script = get_speech_script(GEMINI_API_KEY, ai_report, user_config, mode)
        
        audio_file = f"voice_{name}_{today}_morning.wav" if mode == "sleep_analysis" else f"voice_{name}_{today}.wav"
        has_audio = await generate_audio_from_text(GEMINI_API_KEY, speech_script, audio_file)
        
        # 4. Gửi Telegram (Kèm Audio)
        if tele_id:
            await send_telegram_report(TELE_TOKEN, ai_report, tele_id, name, audio_file if has_audio else None)
        else:
            print(f"[{name}] ⚠️ Không có Chat ID, không gửi tin.")
        
        # Xóa file audio tạm
        if has_audio and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except: pass
            
    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="daily", help="Mode: daily (chiều) hoặc sleep_analysis (sáng)")
    args = parser.parse_args()
    mode = args.mode

    print(f"=== GARMIN AI COACH PRO: MODE {mode.upper()} ===")
    
    # Lấy danh sách user từ Notion logic mới
    users = get_users_from_notion()
    
    if not users:
        print("⚠️ Không tìm thấy user nào Active trên Notion.")
        return

    print(f"🚀 Kích hoạt quy trình cho {len(users)} người dùng...")
    
    tasks = [process_single_user(user, mode) for user in users]
    await asyncio.gather(*tasks)
    print("\n=== HOÀN TẤT ===")

if __name__ == "__main__":
    asyncio.run(main())