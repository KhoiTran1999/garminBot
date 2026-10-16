import os
import asyncio
import argparse
from datetime import date
import time
import logging
from dotenv import load_dotenv
from garminconnect import Garmin

# Tắt cảnh báo 429 từ garminconnect
logging.getLogger("garminconnect").setLevel(logging.CRITICAL)

# Import Services
from backend.services.notion_service import get_users_from_notion, get_user_by_email
from backend.services.garmin_service import get_processed_data, fetch_daily_activities_detailed, check_garmin_sync_status
from backend.services.ai_service import (
    get_ai_advice,
    get_workout_analysis_advice,
    get_battery_analysis_advice,
    get_speech_script,
    generate_audio_from_text,
    get_customer_service_advice,
)
from backend.services.prompt_service import get_prompts_from_notion
from backend.services.weather_service import WeatherService
from backend.services.redis_service import redis_service
from backend.config import Config


def login_garmin(email, password, name):
    """
    Đăng nhập Garmin có check token cache từ Environment Variables, Redis và local file để tránh 429 (Too Many Requests).
    """
    # 1. Hỗ trợ lấy Token từ Environment Variables hoặc Redis Cache
    env_token_key = f"GARMINTOKENS_{email.replace('@', '_').replace('.', '_').upper()}"
    token_string = os.getenv(env_token_key) or os.getenv("GARMINTOKENS") or redis_service.get_garmin_tokens(email)

    # Hỗ trợ môi trường Serverless (Vercel, AWS Lambda) nơi root dir là read-only
    import tempfile
    clean_email = email.replace('@', '_').replace('.', '_')
    try:
        token_dir = os.path.join(os.getcwd(), "tokens", email)
        os.makedirs(token_dir, exist_ok=True)
    except (OSError, PermissionError):
        token_dir = os.path.join(tempfile.gettempdir(), "tokens", clean_email)
        os.makedirs(token_dir, exist_ok=True)

    client = Garmin(email, password)

    try:
        if token_string:
            import base64
            try:
                os.environ["GARMINTOKENS"] = token_string
                client.login(tokenstore=token_string)
                print(f"[{name}] ✅ Đăng nhập Garmin bằng Token thành công.")
            except Exception as e1:
                print(f"[{name}] ⚠️ Lỗi đọc trực tiếp token_string, thử decode ra file... {e1}")
                import json
                try:
                    tokens = json.loads(base64.b64decode(token_string).decode('utf-8'))
                    with open(os.path.join(token_dir, "oauth1_token.json"), "w") as f1:
                        json.dump(tokens[0], f1)
                    with open(os.path.join(token_dir, "oauth2_token.json"), "w") as f2:
                        json.dump(tokens[1], f2)
                    client.login(tokenstore=token_dir)
                    print(f"[{name}] ✅ Đăng nhập Garmin bằng Token decode thành công.")
                except Exception as e2:
                    print(f"[{name}] ⚠️ Lỗi decode token: {e2}. Chuyển sang password.")
                    raise e2

            # Đồng bộ / làm mới token hợp lệ vào Redis
            try:
                redis_service.save_garmin_tokens(email, client.garth.dumps())
            except Exception:
                pass
        else:
            client.login(tokenstore=token_dir)
            print(f"[{name}] ✅ Đăng nhập Garmin bằng Token bảo lưu thành công.")
            try:
                redis_service.save_garmin_tokens(email, client.garth.dumps())
            except Exception:
                pass
    except Exception as e:
        print(f"[{name}] ℹ️ Không dùng được Token. Chuyển sang đăng nhập Password...")
        client.login()
        try:
            os.makedirs(token_dir, exist_ok=True)
            client.garth.dump(token_dir)
            # Lưu ngay token mới vào Redis
            try:
                redis_service.save_garmin_tokens(email, client.garth.dumps())
                print(f"[{name}] ✅ Đã lưu Garmin token mới vào Redis cache.")
            except Exception as redis_save_err:
                print(f"[{name}] ⚠️ Lỗi lưu token vào Redis: {redis_save_err}")
            print(f"[{name}] ✅ Đăng nhập Garmin thành công & đã lưu Token mới.")
        except Exception as save_err:
            print(f"[{name}] ⚠️ Lỗi lưu Token: {save_err}")
    return client


async def handle_daily_or_sleep(user_config, mode, prompts, user_note=None):
    """
    Xử lý báo cáo hàng ngày (Daily) hoặc phân tích giấc ngủ (Sleep Analysis).
    """
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')

    if not email or not password:
        print(f"[{name}] ❌ Thiếu Email/Pass, bỏ qua.")
        return

    # --- RATE LIMITER & DEDUPLICATION ---
    today = date.today()
    date_iso = today.isoformat()

    if redis_service.is_rate_limited(email, mode):
        print(f"[{name}] ⚠️ Bạn đã yêu cầu quá nhanh. Vui lòng thử lại sau 10 phút.")
        return

    if not redis_service.check_and_set_dedup(email, date_iso, mode):
        print(f"[{name}] ⛔ Báo cáo {mode} của bạn đã được tạo trong 1 giờ qua. Vui lòng đợi 1 tiếng giữa các yêu cầu.")
        return
    # ------------------------------------

    try:
        client = login_garmin(email, password, name)

        # --- FRESHNESS CHECK ---
        is_fresh, fresh_msg = check_garmin_sync_status(client, max_age_hours=1.0, user_label=name)
        if not is_fresh:
            print(f"[{name}] ⛔ {fresh_msg}")
            redis_service.delete_dedup(email, date_iso, mode)
            return
        # -----------------------

        today = date.today()

        # 1. Lấy dữ liệu Garmin (Sleep + Stats)
        r_data, r_score, l_data = get_processed_data(client, today, name)

        # 2. Gọi AI
        aqi_data = WeatherService.get_aqi_data()
        
        prompt_key = "sleep_analysis" if mode == "sleep_analysis" else "daily_report"
        advice_template = prompts.get(prompt_key)
        
        if advice_template:
            print(f"[{name}] ℹ️ Using Prompt: '{prompt_key}' (Model: {advice_template.get('model', 'default')})")
        else:
            print(f"[{name}] ⚠️ Prompt '{prompt_key}' not found in Notion. Using Hardcoded Fallback.")

        ai_report = get_ai_advice(today, r_data, r_score, l_data, user_config, prompt_template=advice_template, mode=mode, aqi_data=aqi_data, user_note=user_note)

        # 3. In báo cáo ra console
        print(f"\n[{name}] 📝 BÁO CÁO ({mode.upper()}):\n{ai_report}\n")

        # 4. Tạo Voice Script & Voice Note trong nền (nếu có Gemini Keys)
        if Config.GEMINI_API_KEYS:
            try:
                voice_template = prompts.get("voice_script")
                speech_script = get_speech_script(ai_report, user_config, prompt_template=voice_template, mode=mode)
                
                audio_file = f"voice_{name}_{today}_morning.wav" if mode == "sleep_analysis" else f"voice_{name}_{today}.wav"
                has_audio = await generate_audio_from_text(speech_script, audio_file)
                if has_audio and os.path.exists(audio_file):
                    print(f"[{name}] 🎙️ Đã tạo tệp audio: {audio_file}")
            except Exception as voice_err:
                print(f"[{name}] ⚠️ Lỗi tạo Voice Note: {voice_err}")
            
    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý ({mode}): {e}")
        redis_service.delete_dedup(email, date_iso, mode)


async def handle_workout_analysis(user_config, prompts, user_note=None):
    """
    Xử lý phân tích bài tập chuyên sâu (Workout Analysis).
    """
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')

    if not email or not password:
        print(f"[{name}] ❌ Thiếu Email/Pass, bỏ qua.")
        return

    # --- RATE LIMITER & DEDUPLICATION ---
    today = date.today()
    date_iso = today.isoformat()
    mode = "workout"

    if redis_service.is_rate_limited(email, mode):
        print(f"[{name}] ⚠️ Bạn đã yêu cầu quá nhanh. Vui lòng thử lại sau 10 phút.")
        return

    if not redis_service.check_and_set_dedup(email, date_iso, mode):
        print(f"[{name}] ⛔ Báo cáo {mode} của bạn đã được tạo trong 1 giờ qua. Vui lòng đợi 1 tiếng giữa các yêu cầu.")
        return
    # ------------------------------------

    try:
        # 1. Login Garmin
        client = login_garmin(email, password, name)

        # --- FRESHNESS CHECK ---
        is_fresh, fresh_msg = check_garmin_sync_status(client, max_age_hours=1.0, user_label=name)
        if not is_fresh:
            print(f"[{name}] ⛔ {fresh_msg}")
            redis_service.delete_dedup(email, date_iso, mode)
            return
        # -----------------------

        today = date.today()

        # 2. Lấy dữ liệu bài tập 24h qua
        activities = fetch_daily_activities_detailed(client, today, name)

        if not activities:
            msg = "Hôm nay bạn không có hoạt động nào để phân tích."
            print(f"[{name}] ⚠️ {msg}")
            redis_service.delete_dedup(email, date_iso, mode)
            return

        # 3. AI Phân tích chuyên sâu
        aqi_data = WeatherService.get_aqi_data()
        
        workout_template = prompts.get("workout_analysis")
        if workout_template:
            print(f"[{name}] ℹ️ Using Prompt: 'workout_analysis' (Model: {workout_template.get('model', 'default')})")
        else:
            print(f"[{name}] ⚠️ Prompt 'workout_analysis' not found in Notion. Using Fallback.")

        ai_report = get_workout_analysis_advice(activities, user_config, prompt_template=workout_template, aqi_data=aqi_data, user_note=user_note)
        
        if not ai_report:
            print(f"[{name}] ⚠️ Không tạo được báo cáo AI.")
            return

        # 4. In báo cáo ra console
        print(f"\n[{name}] 📊 BÁO CÁO PHÂN TÍCH BÀI TẬP:\n{ai_report}\n")

        # 5. Tạo Voice Script & Voice Note trong nền
        if Config.GEMINI_API_KEYS:
            try:
                voice_template = prompts.get("voice_script")
                voice_script = get_speech_script(ai_report, user_config, prompt_template=voice_template, mode="daily")
                
                audio_file = f"voice_workout_{name}_{today}.wav"
                has_audio = await generate_audio_from_text(voice_script, audio_file)
                if has_audio and os.path.exists(audio_file):
                    print(f"[{name}] 🎙️ Đã tạo tệp audio: {audio_file}")
            except Exception as voice_err:
                print(f"[{name}] ⚠️ Lỗi tạo Voice Note: {voice_err}")

    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý Workout: {e}")
        redis_service.delete_dedup(email, date_iso, mode)


async def handle_battery_analysis(user_config, prompts, user_note=None):
    """
    Xử lý phân tích năng lượng chuyên biệt (Body Battery & Stress).
    """
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')

    if not email or not password:
        print(f"[{name}] ❌ Thiếu Email/Pass, bỏ qua.")
        return

    # --- RATE LIMITER & DEDUPLICATION ---
    today = date.today()
    date_iso = today.isoformat()
    mode = "battery"

    if redis_service.is_rate_limited(email, mode):
        print(f"[{name}] ⚠️ Bạn đã yêu cầu quá nhanh. Vui lòng thử lại sau 10 phút.")
        return

    if not redis_service.check_and_set_dedup(email, date_iso, mode):
        print(f"[{name}] ⛔ Báo cáo {mode} của bạn đã được tạo trong 1 giờ qua. Vui lòng đợi 1 tiếng giữa các yêu cầu.")
        return
    # ------------------------------------

    try:
        client = login_garmin(email, password, name)

        # --- FRESHNESS CHECK ---
        is_fresh, fresh_msg = check_garmin_sync_status(client, max_age_hours=1.0, user_label=name)
        if not is_fresh:
            print(f"[{name}] ⛔ {fresh_msg}")
            redis_service.delete_dedup(email, date_iso, mode)
            return
        # -----------------------

        today = date.today()

        # 1. Kéo data đã tổng hợp (gồm Timeseries)
        r_data, r_score, l_data = get_processed_data(client, today, name)

        # 2. Gọi AI
        aqi_data = WeatherService.get_aqi_data()

        battery_template = prompts.get("battery_analysis")
        if battery_template:
            print(f"[{name}] ℹ️ Using Prompt: 'battery_analysis' (Model: {battery_template.get('model', 'default')})")
        else:
            print(f"[{name}] ⚠️ Prompt 'battery_analysis' not found in Notion. Using Fallback.")

        ai_report = get_battery_analysis_advice(today, r_data, user_config, prompt_template=battery_template, aqi_data=aqi_data, user_note=user_note)

        if not ai_report:
            print(f"[{name}] ⚠️ Không tạo được báo cáo AI.")
            return

        # 3. In báo cáo ra console
        print(f"\n[{name}] 🔋 BÁO CÁO NĂNG LƯỢNG:\n{ai_report}\n")

        # 4. Tạo Voice Script & Audio
        if Config.GEMINI_API_KEYS:
            try:
                voice_template = prompts.get("voice_script")
                voice_script = get_speech_script(ai_report, user_config, prompt_template=voice_template, mode="battery")

                audio_file = f"voice_battery_{name}_{today}.wav"
                has_audio = await generate_audio_from_text(voice_script, audio_file)
                if has_audio and os.path.exists(audio_file):
                    print(f"[{name}] 🎙️ Đã tạo tệp audio: {audio_file}")
            except Exception as voice_err:
                print(f"[{name}] ⚠️ Lỗi tạo Voice Note: {voice_err}")

    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý Battery Analysis: {e}")
        redis_service.delete_dedup(email, date_iso, mode)


async def handle_ask(user_config, question, prompts):
    """
    Xử lý câu hỏi của người dùng (Customer Service Q&A & Garmin Data Retrieval).
    """
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')

    if not email:
        print(f"[{name}] ❌ Thiếu Email, bỏ qua.")
        return

    clean_question = (question or "").strip()
    if not clean_question or clean_question.lower() in ["none", "null"]:
        print(f"[{name}] ⚠️ Vui lòng cung cấp câu hỏi sau flag --question.")
        return

    # Rate Limiter cho Chat / Ask (tối đa 15 câu trong 10 phút)
    if redis_service.is_rate_limited(email, "ask", limit=15, window_seconds=600):
        print(f"[{name}] ⚠️ Bạn đang gửi câu hỏi quá nhanh. Vui lòng thử lại sau vài phút.")
        return

    try:
        # Lấy template prompt từ Notion nếu có (có cache)
        ask_template = prompts.get("ask_help")
        if ask_template:
            print(f"[{name}] ℹ️ Using Prompt: 'ask_help' (Model: {ask_template.get('model', 'default')})")
        else:
            print(f"[{name}] ⚠️ Prompt 'ask_help' not found in Notion. Using Fallback.")

        # Đăng nhập Garmin Connect (tận dụng token cache từ Redis)
        client = None
        if email and password:
            try:
                client = login_garmin(email, password, name)
                print(f"[{name}] 🧠 Garmin client loaded for Agent.")
            except Exception as ge:
                print(f"[{name}] ⚠️ Lỗi đăng nhập Garmin Connect: {ge}")

        # Gọi AI CS (Agent / Tool Calling)
        ai_reply = await get_customer_service_advice(
            user_id=email,
            question=clean_question,
            user_config=user_config,
            prompt_template=ask_template,
            garmin_client=client
        )

        print(f"\n[{name}] 💬 TRẢ LỜI CÂU HỎI:\n{ai_reply}\n")

    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý hỏi đáp: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Garmin AI Coach Pro")
    parser.add_argument("--mode", default="daily", help="Mode: daily | sleep_analysis | workout | battery | ask")
    parser.add_argument("--email", default=None, help="Filter specific user by Email")
    parser.add_argument("--question", default=None, help="The question text for Q&A mode")

    args = parser.parse_args()
    mode = args.mode
    filter_email = args.email
    question = args.question or os.getenv("CLIENT_QUESTION")
    if question and str(question).strip().lower() in ["none", "null", ""]:
        question = None

    print(f"=== GARMIN AI COACH PRO: MODE {mode.upper()} ===")
    if filter_email:
        print(f"Filter User Email: {filter_email}")

    try:
        # 1. LẤY USER
        if filter_email:
            user = get_user_by_email(filter_email)
            if user:
                users = [user]
            else:
                all_users = get_users_from_notion()
                users = [u for u in all_users if str(u.get('email', '')).strip().lower() == str(filter_email).strip().lower()]

                if not users:
                    print(f"User with Email {filter_email} not found or inactive on Notion.")
                    return
        else:
            users = get_users_from_notion()
            if not users:
                print("⚠️ Không tìm thấy user nào Active trên Notion.")
                return

        print(f"🚀 Kích hoạt quy trình cho {len(users)} người dùng...")

        # 2. Lấy Prompts (tận dụng Redis cache)
        prompts = get_prompts_from_notion(use_cache=True)

        tasks = []
        for user in users:
            if mode == "workout":
                tasks.append(handle_workout_analysis(user, prompts, user_note=question))
            elif mode == "battery":
                tasks.append(handle_battery_analysis(user, prompts, user_note=question))
            elif mode == "ask":
                tasks.append(handle_ask(user, question, prompts))
            elif mode in ["daily", "daily_report", "sleep_analysis"]:
                run_mode = "sleep_analysis" if mode == "sleep_analysis" else "daily"
                tasks.append(handle_daily_or_sleep(user, run_mode, prompts, user_note=question))
            else:
                print(f"Unknown mode: {mode}")
                return

        await asyncio.gather(*tasks)
        print("\n=== COMPLETE ===")

    except Exception as e:
        error_msg = f"CRITICAL ERROR in main.py (Mode: {mode}):\n{str(e)}"
        print(f"Error: {error_msg}")
        raise e

if __name__ == "__main__":
    asyncio.run(main())
