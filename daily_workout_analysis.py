import os
import asyncio
import argparse
from datetime import date
from dotenv import load_dotenv
from garminconnect import Garmin

# Import Services
from app.services.notion_service import get_users_from_notion
from app.services.garmin_service import fetch_daily_activities_detailed
from app.services.ai_service import get_workout_analysis_advice, get_speech_script, generate_audio_from_text
from app.services.telegram_service import send_telegram_report

# --- CẤU HÌNH ---
load_dotenv()
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def process_user_workout_analysis(user_config):
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')
    tele_id = user_config.get('telegram_chat_id')

    if not email or not password:
        print(f"[{name}] ❌ Thiếu Email/Pass, bỏ qua.")
        return

    try:
        # 1. Login Garmin
        client = Garmin(email, password)
        client.login()
        print(f"[{name}] ✅ Đăng nhập Garmin thành công.")
        
        today = date.today()
        
        # 2. Lấy dữ liệu bài tập 24h qua
        activities = fetch_daily_activities_detailed(client, today, name)
        
        if not activities:
            print(f"[{name}] ⚠️ Không có bài tập nào hôm nay.")
            # Có thể gửi thông báo ngắn nếu muốn, hoặc im lặng
            return

        # 3. AI Phân tích chuyên sâu
        ai_report = get_workout_analysis_advice(GEMINI_API_KEY, activities, user_config)
        
        if not ai_report:
            print(f"[{name}] ⚠️ Không tạo được báo cáo AI.")
            return

        # 4. Tạo Voice Script & Audio
        # Dùng lại hàm get_speech_script nhưng với context workout được xử lý bên trong (mode="workout")
        # Tuy nhiên hàm hiện tại chỉ support "daily" và "sleep_analysis". 
        # Ta có thể dùng "daily" tạm hoặc update hàm đó. 
        # Để đơn giản và nhanh, ta dùng "daily" vì prompt khá generic ("báo cáo thể thao")
        
        import time
        time.sleep(60) # Wait 60s before next AI call to avoid Rate Limit (Free Tier)
        
        voice_script = get_speech_script(GEMINI_API_KEY, ai_report, user_config, mode="daily")
        
        audio_file = f"voice_workout_{name}_{today}.wav"
        has_audio = await generate_audio_from_text(GEMINI_API_KEY, voice_script, audio_file)

        # 5. Gửi Telegram
        if tele_id:
            await send_telegram_report(TELE_TOKEN, ai_report, tele_id, name, audio_file if has_audio else None)
        else:
            print(f"[{name}] ⚠️ Không có Chat ID.")

        # Cleanup
        if has_audio and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except: pass

    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý Workout Analysis: {e}")

async def main():
    print("=== DAILY WORKOUT ANALYSIS (20:00 PM) ===")
    
    users = get_users_from_notion()
    
    if not users:
        print("⚠️ Không tìm thấy user nào Active.")
        return

    print(f"🚀 Kích hoạt phân tích bài tập cho {len(users)} người dùng...")
    
    tasks = [process_user_workout_analysis(user) for user in users]
    await asyncio.gather(*tasks)
    print("\n=== HOÀN TẤT ===")

if __name__ == "__main__":
    asyncio.run(main())
