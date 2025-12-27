import os
import math
import json
import asyncio
from datetime import date, timedelta
from dotenv import load_dotenv

# Thư viện
from garminconnect import Garmin
from telegram import Bot
from google import genai 

# --- CẤU HÌNH ---
load_dotenv()
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASS = os.getenv("GARMIN_PASS")
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELE_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình cửa sổ quét (7 ngày cho Acute Load)
DAYS_WINDOW = 7

# ==============================================================================
# 1. MODULE TÍNH TOÁN KHOA HỌC (Metrics Calculation)
# ==============================================================================

def calculate_readiness_score(data):
    """Tính điểm Sẵn sàng (0-100) dựa trên Sleep, Stress, BodyBattery"""
    # 1. Sleep Score
    hours_sleep = data['sleep_seconds'] / 3600
    if hours_sleep < 5: sleep_score = 30
    elif hours_sleep < 6.5: sleep_score = 50
    elif hours_sleep < 7.5: sleep_score = 75
    else: sleep_score = 100
    
    # 2. Stress Score (Thấp là tốt)
    avg_stress = data['stress']
    if avg_stress <= 25: stress_score = 100
    elif avg_stress <= 35: stress_score = 80
    elif avg_stress <= 50: stress_score = 50
    else: stress_score = 20
    
    # 3. Body Battery
    bb_score = data['body_battery']
    
    # 4. Trọng số: 40% Sleep, 20% Stress, 40% Body Battery
    weighted_score = (0.4 * sleep_score) + (0.2 * stress_score) + (0.4 * bb_score)
    
    # Limiting Factor: Nếu Body Battery < 20 (Cạn kiệt), Readiness không quá 30
    final_score = weighted_score
    if bb_score < 20:
        final_score = min(weighted_score, 30)
        
    return int(final_score)

def calculate_trimp_banister(duration_min, avg_hr, rhr, max_hr):
    """Tính TRIMP (Training Impulse) theo công thức Banister"""
    if max_hr <= rhr or avg_hr <= rhr: return 0
    hr_ratio = (avg_hr - rhr) / (max_hr - rhr)
    return duration_min * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)

# ==============================================================================
# 2. MODULE THU THẬP & XỬ LÝ DỮ LIỆU (Data Processing)
# ==============================================================================

def get_processed_data(client, today):
    print("🔄 [1/3] Đang thu thập dữ liệu từ Garmin...")
    
    # --- A. Lấy dữ liệu Sức khỏe (Readiness) hôm nay ---
    readiness_data = {"rhr": 0, "stress": 0, "body_battery": 0, "sleep_seconds": 0, "nap_seconds": 0}
    try:
        summary = client.get_user_summary(today.isoformat())
        stats = summary.get('stats', summary)
        
        readiness_data['rhr'] = stats.get('restingHeartRate', 0)
        readiness_data['stress'] = stats.get('averageStressLevel', 0)
        
        # Ưu tiên lấy Body Battery mới nhất
        bb_val = summary.get('stats_and_body', {}).get('bodyBatteryMostRecentValue')
        if bb_val is None: bb_val = stats.get('bodyBatteryMostRecentValue', 0)
        readiness_data['body_battery'] = bb_val
        
        readiness_data['sleep_seconds'] = stats.get('sleepingSeconds', 0)
        
        # Quét Event để tìm NAP (Giấc ngủ trưa)
        events = stats.get('bodyBatteryActivityEventList', [])
        for e in events:
            if e.get('eventType') == 'NAP':
                readiness_data['nap_seconds'] += e.get('durationInMilliseconds', 0) / 1000
                
    except Exception as e:
        print(f"⚠️ Lỗi lấy dữ liệu Readiness: {e}")

    readiness_score = calculate_readiness_score(readiness_data)

    # --- B. Lấy dữ liệu Tải tập luyện (Training Load) 7 ngày ---
    load_stats = {
        "avg_daily_load": 0,
        "final_calc_max_hr": 0,
        "raw_activities_for_ai": []
    }
    
    try:
        start_date = today - timedelta(days=DAYS_WINDOW - 1)
        activities = client.get_activities_by_date(start_date.isoformat(), today.isoformat(), "")
        
        current_max_hr = 185 # Fallback mặc định
        rhr_input = readiness_data['rhr'] if readiness_data['rhr'] > 30 else 55 # Fallback RHR
        
        total_trimp = 0
        
        for act in activities:
            name = act.get('activityName', 'Unknown')
            duration_min = act.get('duration', 0) / 60
            avg_hr = act.get('averageHR', 0)
            mx_hr = act.get('maxHR', 0)
            date_str = act.get('startTimeLocal', '')[:10]
            
            # Cập nhật Max HR thực tế (quan trọng để tính TRIMP chuẩn)
            if mx_hr > load_stats['final_calc_max_hr']:
                load_stats['final_calc_max_hr'] = mx_hr
                if mx_hr > 160: current_max_hr = mx_hr # Chỉ update nếu > 160 (tránh lỗi)

            # Tính TRIMP
            trimp = 0
            if avg_hr > rhr_input:
                trimp = calculate_trimp_banister(duration_min, avg_hr, rhr_input, current_max_hr)
            
            total_trimp += trimp
            
            # Lưu log để gửi AI
            if trimp > 5: # Chỉ log bài tập có ý nghĩa
                load_stats['raw_activities_for_ai'].append(
                    f"- {date_str}: {name} ({int(duration_min)}p) | MaxHR {mx_hr} | TRIMP {int(trimp)}"
                )

        load_stats['avg_daily_load'] = total_trimp / DAYS_WINDOW # Acute Load
        load_stats['final_calc_max_hr'] = current_max_hr

    except Exception as e:
        print(f"⚠️ Lỗi lấy dữ liệu Load: {e}")

    return readiness_data, readiness_score, load_stats

# ==============================================================================
# 3. MODULE AI ANALYST (Generate Report)
# ==============================================================================

def get_ai_advice(today, r_data, r_score, l_data):
    print("🧠 [2/3] Đang gọi AI Coach (Gemini)...")
    if not GEMINI_API_KEY:
        return "⚠️ Lỗi: Chưa cấu hình GEMINI_API_KEY."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Xây dựng Prompt
        activities_text = "\n".join(l_data['raw_activities_for_ai']) if l_data['raw_activities_for_ai'] else "Không có hoạt động đáng kể."
        
        prompt = f"""
        Bạn là Huấn luyện viên thể thao chuyên nghiệp (AI Running Coach). 
        Hãy phân tích dữ liệu ngày {today} và đưa ra lời khuyên ngắn gọn cho VĐV.

        ### 1. DỮ LIỆU SỨC KHỎE (READINESS)
        - **Điểm Sẵn sàng:** {r_score}/100 (Thang điểm: <40 Kém, 40-70 TB, >70 Tốt)
        - **Cơ thể:** Pin {r_data['body_battery']}/100 | Stress {r_data['stress']} (Thấp <25, Cao >50)
        - **Giấc ngủ:** Đêm {round(r_data['sleep_seconds']/3600, 1)}h + Trưa {int(r_data['nap_seconds']//60)}p
        - **Nhịp tim nghỉ (RHR):** {r_data['rhr']} bpm

        ### 2. DỮ LIỆU TẢI TẬP LUYỆN (7 NGÀY)
        - **Tải trung bình ngày (Acute Load):** {int(l_data['avg_daily_load'])} (TRIMP Index)
        - **Max HR thực tế:** {l_data['final_calc_max_hr']} bpm
        - **Lịch sử hoạt động:**
        {activities_text}

        ### YÊU CẦU OUTPUT (Markdown):
        Hãy trả về báo cáo theo cấu trúc sau (dùng icon sinh động):
        
        **🔥 ĐÁNH GIÁ TRẠNG THÁI**
        [Tóm tắt ngắn gọn tình trạng cơ thể: Sung sức hay Mệt mỏi? Yếu tố nào đang kìm hãm (Ngủ ít/Stress/Pin thấp)?]

        **🎯 PHÂN TÍCH TẢI TẬP LUYỆN**
        [Nhận xét về cường độ tập luyện tuần qua. Tải này là Duy trì, Tích lũy hay Quá tải?]

        **🏃 BÀI TẬP ĐỀ XUẤT HÔM NAY**
        * **Chỉ định:** [Nghỉ ngơi / Chạy nhẹ Zone 2 / Bài Interval...]
        * **Chi tiết:** [Ví dụ: Chạy 30p pace 6:30 hoặc Nghỉ hoàn toàn]

        **💡 TIP PHỤC HỒI**
        [Một lời khuyên dinh dưỡng hoặc giấc ngủ cụ thể]
        """

        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Hoặc gemini-1.5-flash
            contents=prompt
        )
        return response.text

    except Exception as e:
        print(f"❌ Lỗi AI: {e}")
        return "AI Coach đang bận, vui lòng thử lại sau."

# ==============================================================================
# 4. MODULE TELEGRAM (Send Report)
# ==============================================================================

async def send_telegram_report(message):
    print("📲 [3/3] Đang gửi báo cáo qua Telegram...")
    if not TELE_TOKEN or not TELE_ID:
        print("⚠️ Chưa cấu hình Telegram Token/ID.")
        return

    try:
        bot = Bot(token=TELE_TOKEN)
        # Gửi tin nhắn (Markdown)
        await bot.send_message(chat_id=TELE_ID, text=message, parse_mode='Markdown')
        print("✅ Đã gửi thành công!")
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")

# ==============================================================================
# MAIN FLOW
# ==============================================================================

async def main():
    print("=== GARMIN AI COACH PRO ===")
    
    # 1. Đăng nhập Garmin
    try:
        if not GARMIN_EMAIL or not GARMIN_PASS:
            print("❌ Thiếu Email/Pass Garmin.")
            return
        client = Garmin(GARMIN_EMAIL, GARMIN_PASS)
        client.login()
        print(f"✅ Đăng nhập: {client.display_name}")
    except Exception as e:
        print(f"❌ Đăng nhập thất bại: {e}")
        return

    today = date.today()
    # today = date(2025, 12, 27) # Uncomment để test ngày cũ
    
    # 2. Lấy & Xử lý dữ liệu
    r_data, r_score, l_data = get_processed_data(client, today)
    
    # 3. Tạo báo cáo AI
    ai_report = get_ai_advice(today, r_data, r_score, l_data)
    
    # In ra console để debug
    print("\n--- REPORT PREVIEW ---")
    print(ai_report)
    print("----------------------")
    
    # 4. Gửi Telegram
    await send_telegram_report(ai_report)

if __name__ == "__main__":
    asyncio.run(main())