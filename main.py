import os
import math
import json
import asyncio
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
import pytz

# Thư viện
from garminconnect import Garmin
from telegram import Bot
from google import genai 

# --- CẤU HÌNH CHUNG ---
load_dotenv()
TELE_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình cửa sổ quét (7 ngày cho Acute Load)
DAYS_WINDOW = 7

# ==============================================================================
# 1. MODULE TÍNH TOÁN KHOA HỌC
# ==============================================================================

def calculate_readiness_score(data):
    """Tính điểm Sẵn sàng (0-100) dựa trên Sleep, Stress, BodyBattery"""
    # data['sleep_hours'] giờ là số giờ ngủ thực tế (đã trừ lúc thức)
    hours_sleep = data.get('sleep_hours', 0)
    
    if hours_sleep < 5: sleep_score = 30
    elif hours_sleep < 6.5: sleep_score = 50
    elif hours_sleep < 7.5: sleep_score = 75
    else: sleep_score = 100
    
    avg_stress = data.get('stress', 50)
    if avg_stress <= 25: stress_score = 100
    elif avg_stress <= 35: stress_score = 80
    elif avg_stress <= 50: stress_score = 50
    else: stress_score = 20
    
    bb_score = data.get('body_battery', 0)
    
    weighted_score = (0.4 * sleep_score) + (0.2 * stress_score) + (0.4 * bb_score)
    
    final_score = weighted_score
    # Phạt nặng nếu Pin cơ thể quá thấp
    if bb_score < 20:
        final_score = min(weighted_score, 30)
        
    return int(final_score)

def calculate_trimp_banister(duration_min, avg_hr, rhr, max_hr):
    """Tính TRIMP (Training Impulse) theo công thức Banister"""
    if max_hr <= rhr or avg_hr <= rhr: return 0
    hr_ratio = (avg_hr - rhr) / (max_hr - rhr)
    return duration_min * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)

def seconds_to_text(seconds):
    """Chuyển giây sang format: Xh Yp"""
    if not seconds: return "0p"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0: return f"{h}h {m}p"
    return f"{m}p"

# ==============================================================================
# 2. MODULE THU THẬP & XỬ LÝ DỮ LIỆU
# ==============================================================================

def get_sleep_analysis(client, date_str, user_label="User"):
    """
    Lấy dữ liệu giấc ngủ chi tiết (Deep, Light, REM) và tạo text cho AI.
    Trả về: (real_sleep_hours, sleep_description_text)
    """
    try:
        # Gọi API lấy dữ liệu giấc ngủ chi tiết
        sleep_data = client.get_sleep_data(date_str)
        dto = sleep_data.get('dailySleepDTO', {})
        
        if not dto:
            return 0, "Không có dữ liệu giấc ngủ chi tiết (Chưa đồng bộ)."

        # Lấy các thành phần (đơn vị: giây)
        deep = dto.get('deepSleepSeconds', 0)
        light = dto.get('lightSleepSeconds', 0)
        rem = dto.get('remSleepSeconds', 0)
        awake = dto.get('awakeSleepSeconds', 0)
        
        # Tính tổng ngủ THỰC TẾ (Không tính Awake)
        real_sleep_sec = deep + light + rem
        real_sleep_hours = real_sleep_sec / 3600

        # Tạo chuỗi text mô tả để gửi cho AI
        sleep_text = (
            f"Tổng ngủ thực: {seconds_to_text(real_sleep_sec)} (đã trừ lúc thức).\n"
            f"   - Ngủ sâu (Deep): {seconds_to_text(deep)}\n"
            f"   - Ngủ nông (Light): {seconds_to_text(light)}\n"
            f"   - Ngủ mơ (REM): {seconds_to_text(rem)}\n"
            f"   - Thời gian thức: {seconds_to_text(awake)}"
        )
        
        return real_sleep_hours, sleep_text

    except AttributeError:
        print(f"[{user_label}] ❌ Lỗi thư viện: Client không có hàm 'get_sleep_data'. Hãy chạy 'pip install --upgrade garminconnect'.")
        return 0, "Lỗi thư viện Garmin cũ."
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy chi tiết giấc ngủ: {e}")
        return 0, "Không lấy được chi tiết giấc ngủ."

def get_processed_data(client, today, user_label="User"):
    print(f"[{user_label}] 🔄 Đang thu thập dữ liệu từ Garmin...")
    
    # Khởi tạo data
    readiness_data = {
        "rhr": 0, 
        "stress": 0, 
        "body_battery": 0, 
        "sleep_hours": 0,
        "nap_seconds": 0,
        "sleep_text": "Chưa có dữ liệu"
    }

    date_iso = today.isoformat()

    # --- A. Lấy chỉ số cơ bản (RHR, Stress, Body Battery) ---
    try:
        summary = client.get_user_summary(date_iso)
        stats = summary.get('stats', summary)
        
        readiness_data['rhr'] = stats.get('restingHeartRate', 0)
        readiness_data['stress'] = stats.get('averageStressLevel', 0)
        
        # Lấy Body Battery mới nhất
        bb_val = summary.get('stats_and_body', {}).get('bodyBatteryMostRecentValue')
        if bb_val is None: bb_val = stats.get('bodyBatteryMostRecentValue', 0)
        readiness_data['body_battery'] = bb_val
        
        # Lấy giấc ngủ ngắn (Nap) nếu có
        events = stats.get('bodyBatteryActivityEventList', [])
        if events:
            for e in events:
                if e.get('eventType') == 'NAP':
                    readiness_data['nap_seconds'] += e.get('durationInMilliseconds', 0) / 1000
                
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy User Summary: {e}")

    # --- B. Lấy chi tiết giấc ngủ (Deep/Light/REM) ---
    real_hours, sleep_desc = get_sleep_analysis(client, date_iso, user_label)
    readiness_data['sleep_hours'] = real_hours
    readiness_data['sleep_text'] = sleep_desc

    # Tính điểm Readiness
    readiness_score = calculate_readiness_score(readiness_data)

    # --- C. Training Load (7 ngày) ---
    load_stats = {"avg_daily_load": 0, "final_calc_max_hr": 0, "raw_activities_for_ai": []}
    
    try:
        start_date = today - timedelta(days=DAYS_WINDOW - 1)
        activities = client.get_activities_by_date(start_date.isoformat(), date_iso, "")
        
        current_max_hr = 185
        rhr_input = readiness_data['rhr'] if readiness_data['rhr'] > 30 else 55
        
        total_trimp = 0
        
        for act in activities:
            name = act.get('activityName', 'Unknown')
            duration_min = act.get('duration', 0) / 60
            avg_hr = act.get('averageHR', 0)
            mx_hr = act.get('maxHR', 0)
            date_str = act.get('startTimeLocal', '')[:10]
            
            if mx_hr > load_stats['final_calc_max_hr']:
                load_stats['final_calc_max_hr'] = mx_hr
                if mx_hr > 160: current_max_hr = mx_hr

            trimp = 0
            if avg_hr > rhr_input:
                trimp = calculate_trimp_banister(duration_min, avg_hr, rhr_input, current_max_hr)
            
            total_trimp += trimp
            
            # Chỉ liệt kê các hoạt động đáng kể
            if trimp > 10: 
                load_stats['raw_activities_for_ai'].append(
                    f"- {date_str}: {name} ({int(duration_min)}p) | MaxHR {mx_hr} | TRIMP {int(trimp)}"
                )

        load_stats['avg_daily_load'] = total_trimp / DAYS_WINDOW
        load_stats['final_calc_max_hr'] = current_max_hr

    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy Activities Load: {e}")

    return readiness_data, readiness_score, load_stats

# ==============================================================================
# 3. MODULE AI ANALYST
# ==============================================================================

def get_ai_advice(today, r_data, r_score, l_data, user_label="User"):
    print(f"[{user_label}] 🧠 Đang gọi AI Coach (Gemini)...")
    if not GEMINI_API_KEY:
        return "⚠️ Lỗi: Chưa cấu hình GEMINI_API_KEY."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        activities_text = "\n".join(l_data['raw_activities_for_ai']) if l_data['raw_activities_for_ai'] else "Không có hoạt động đáng kể."
        
        # Lấy giờ VN
        vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        current_now = datetime.now(vn_timezone).strftime("%H:%M:%S, %d/%m/%Y")
        
        nap_text = f"+ Ngủ trưa: {int(r_data['nap_seconds']//60)} phút" if r_data['nap_seconds'] > 0 else ""

        prompt = f"""
        Bạn là Huấn luyện viên thể thao chuyên nghiệp (AI Running Coach).
        Hãy phân tích dữ liệu ngày {today} và đưa ra lời khuyên ngắn gọn cho VĐV tên {user_label}.
        Thời gian báo cáo: {current_now}

        1. DỮ LIỆU SỨC KHỎE (QUAN TRỌNG)
        - **Điểm Sẵn sàng:** {r_score}/100
        - **Cơ thể:** Pin Body Battery {r_data['body_battery']}/100 | Stress {r_data['stress']} (Thấp <25, Cao >50)
        - **Chi tiết Giấc ngủ:** {r_data['sleep_text']}
           {nap_text}
        - **Nhịp tim nghỉ (RHR):** {r_data['rhr']} bpm

        2. DỮ LIỆU TẢI TẬP LUYỆN (7 NGÀY QUA)
        - **Tải trung bình ngày (Acute Load):** {int(l_data['avg_daily_load'])} (TRIMP Index)
        - **Lịch sử hoạt động gần đây:**
        {activities_text}

        YÊU CẦU OUTPUT (Markdown Telegram):
        Trả về báo cáo ngắn gọn, dùng icon sinh động:

        **🔢 TỔNG QUAN HÔM NAY**
        [Tóm tắt nhanh các chỉ số. Nhấn mạnh vào chất lượng giấc ngủ (Sâu/REM) nếu nó tốt hoặc xấu.]

        **🔥 ĐÁNH GIÁ TRẠNG THÁI**
        [Cơ thể đang Sung sức hay Mệt mỏi? Giấc ngủ tối qua ảnh hưởng thế nào đến sự phục hồi hôm nay?]

        **🏃 BÀI TẬP ĐỀ XUẤT**
        [Dựa trên điểm Sẵn sàng và Tải tập luyện, đề xuất có nên tập hay nghỉ ngơi. Nếu tập, gợi ý cường độ và loại bài tập phù hợp.]

        **💡 TIP HỒI PHỤC**
        [Mẹo nhanh để cải thiện giấc ngủ và phục hồi cơ thể hiệu quả hơn.]
        """

        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Hoặc gemini-1.5-flash
            contents=prompt
        )
        return response.text

    except Exception as e:
        print(f"[{user_label}] ❌ Lỗi AI: {e}")
        return "AI Coach đang bận, vui lòng thử lại sau."

# ==============================================================================
# 4. MODULE TELEGRAM & MAIN FLOW
# ==============================================================================

async def send_telegram_report(message, chat_id, user_label="User"):
    print(f"[{user_label}] 📲 Đang gửi báo cáo qua Telegram...")
    if not TELE_TOKEN or not chat_id:
        return

    bot = Bot(token=TELE_TOKEN)
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"[{user_label}] ✅ Gửi thành công!")
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi Markdown, gửi Plain Text: {e}")
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=None)

async def process_single_user(user_config):
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')
    tele_id = user_config.get('telegram_chat_id')

    if not email or not password: return

    try:
        # Đăng nhập
        client = Garmin(email, password)
        client.login()
        print(f"[{name}] ✅ Đăng nhập thành công.")
        
        today = date.today()
        # today = date(2025, 12, 30) # Hardcode để test ngày cụ thể

        # Xử lý dữ liệu
        r_data, r_score, l_data = get_processed_data(client, today, name)

        # AI Phân tích
        ai_report = get_ai_advice(today, r_data, r_score, l_data, name)

        # Gửi Telegram
        if tele_id:
            await send_telegram_report(ai_report, tele_id, name)
            
    except Exception as e:
        print(f"[{name}] ❌ Lỗi: {e}")

async def main():
    print("=== GARMIN AI COACH PRO ===")
    users_json = os.getenv("USERS_JSON")
    if not users_json:
        print("❌ Thiếu USERS_JSON")
        return

    try:
        users = json.loads(users_json)
        tasks = [process_single_user(user) for user in users]
        await asyncio.gather(*tasks)
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    asyncio.run(main())