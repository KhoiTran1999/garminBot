import os
import asyncio
import argparse
from datetime import date
import time
from dotenv import load_dotenv
from garminconnect import Garmin

# Import Services
from app.services.notion_service import get_users_from_notion
from app.services.garmin_service import get_processed_data, fetch_daily_activities_detailed
from app.services.ai_service import get_ai_advice, get_workout_analysis_advice, get_speech_script, generate_audio_from_text
from app.services.prompt_service import get_prompts_from_notion
from app.services.prompt_service import get_prompts_from_notion
from app.services.telegram_service import send_telegram_report, send_error_alert

# --- CẤU HÌNH CHUNG ---
from app.config import Config

# --- CẤU HÌNH CHUNG ---
# --- CẤU HÌNH CHUNG ---
TELE_TOKEN = Config.TELEGRAM_TOKEN
TELE_ADMIN = Config.TELEGRAM_ADMIN_ID

async def handle_daily_or_sleep(user_config, mode, prompts):
    """
    Xử lý báo cáo hàng ngày (Daily) hoặc phân tích giấc ngủ (Sleep Analysis).
    """
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

        # 2. Gọi AI
        prompt_key = "sleep_analysis" if mode == "sleep_analysis" else "daily_report"
        advice_template = prompts.get(prompt_key)
        
        if advice_template:
            print(f"[{name}] ℹ️ Using Prompt: '{prompt_key}' (Model: {advice_template.get('model', 'default')})")
        else:
            print(f"[{name}] ⚠️ Prompt '{prompt_key}' not found in Notion. Using Hardcoded Fallback.")

        ai_report = get_ai_advice(today, r_data, r_score, l_data, user_config, prompt_template=advice_template, mode=mode)

        # 3. Tạo Voice Script & Audio
        voice_template = prompts.get("voice_script")
        speech_script = get_speech_script(ai_report, user_config, prompt_template=voice_template, mode=mode)
        
        audio_file = f"voice_{name}_{today}_morning.wav" if mode == "sleep_analysis" else f"voice_{name}_{today}.wav"
        has_audio = await generate_audio_from_text(speech_script, audio_file)
        
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
        print(f"[{name}] ❌ Lỗi xử lý ({mode}): {e}")

async def handle_workout_analysis(user_config, prompts):
    """
    Xử lý phân tích bài tập chuyên sâu (Workout Analysis).
    """
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
            return

        # 3. AI Phân tích chuyên sâu
        workout_template = prompts.get("workout_analysis")
        if workout_template:
            print(f"[{name}] ℹ️ Using Prompt: 'workout_analysis' (Model: {workout_template.get('model', 'default')})")
        else:
             print(f"[{name}] ⚠️ Prompt 'workout_analysis' not found in Notion. Using Fallback.")

        ai_report = get_workout_analysis_advice(activities, user_config, prompt_template=workout_template)
        
        if not ai_report:
            print(f"[{name}] ⚠️ Không tạo được báo cáo AI.")
            return

        # 4. Tạo Voice Script & Audio
        # Để tránh Rate Limit khi gọi liên tiếp
        time.sleep(5) 
        
        voice_template = prompts.get("voice_script")
        # Dùng mode="daily" tạm cho context thể thao
        voice_script = get_speech_script(ai_report, user_config, prompt_template=voice_template, mode="daily")
        
        audio_file = f"voice_workout_{name}_{today}.wav"
        has_audio = await generate_audio_from_text(voice_script, audio_file)

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
        print(f"[{name}] ❌ Lỗi xử lý Workout: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Garmin AI Coach Pro")
    parser.add_argument("--mode", default="daily", help="Mode: daily | sleep_analysis | workout")
    args = parser.parse_args()
    mode = args.mode

    print(f"=== GARMIN AI COACH PRO: MODE {mode.upper()} ===")
    
    try:
        # 1. Lấy user từ Notion
        users = get_users_from_notion()
        if not users:
            print("⚠️ Không tìm thấy user nào Active trên Notion.")
            return

        print(f"🚀 Kích hoạt quy trình cho {len(users)} người dùng...")
        
        # 2. Lấy Prompts
        prompts = get_prompts_from_notion()
        
        tasks = []
        for user in users:
            if mode == "workout":
                tasks.append(handle_workout_analysis(user, prompts))
            elif mode in ["daily", "daily_report", "sleep_analysis"]:
                # Clean up mode string explicitly if needed
                run_mode = "sleep_analysis" if mode == "sleep_analysis" else "daily"
                tasks.append(handle_daily_or_sleep(user, run_mode, prompts))
            else:
                print(f"❌ Unknown mode: {mode}")
                return

        await asyncio.gather(*tasks)
        print("\n=== HOÀN TẤT ===")

    except Exception as e:
        error_msg = f"CRITICAL ERROR in main.py (Mode: {mode}):\n{str(e)}"
        print(f"❌ {error_msg}")
        # Gửi alert
        if TELE_ADMIN:
             await send_error_alert(TELE_TOKEN, TELE_ADMIN, error_msg)
        else:
             print("⚠️ Config TELEGRAM_ADMIN_ID chưa được set, không gửi alert.")
        raise e # Re-raise để GitHub Actions vẫn báo fail

if __name__ == "__main__":
    asyncio.run(main())