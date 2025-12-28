import os
import math
import json
import asyncio
from datetime import date, timedelta
from dotenv import load_dotenv
from datetime import datetime

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
# 1. MODULE TÍNH TOÁN KHOA HỌC (Giữ nguyên)
# ==============================================================================

def calculate_readiness_score(data):
    """Tính điểm Sẵn sàng (0-100) dựa trên Sleep, Stress, BodyBattery"""
    hours_sleep = data['sleep_seconds'] / 3600
    if hours_sleep < 5: sleep_score = 30
    elif hours_sleep < 6.5: sleep_score = 50
    elif hours_sleep < 7.5: sleep_score = 75
    else: sleep_score = 100
    
    avg_stress = data['stress']
    if avg_stress <= 25: stress_score = 100
    elif avg_stress <= 35: stress_score = 80
    elif avg_stress <= 50: stress_score = 50
    else: stress_score = 20
    
    bb_score = data['body_battery']
    
    weighted_score = (0.4 * sleep_score) + (0.2 * stress_score) + (0.4 * bb_score)
    
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
# 2. MODULE THU THẬP & XỬ LÝ DỮ LIỆU (Giữ nguyên logic, thêm tham số user_label)
# ==============================================================================

def get_processed_data(client, today, user_label="User"):
    print(f"[{user_label}] 🔄 Đang thu thập dữ liệu từ Garmin...")
    
    # --- A. Readiness ---
    readiness_data = {"rhr": 0, "stress": 0, "body_battery": 0, "sleep_seconds": 0, "nap_seconds": 0}
    try:
        summary = client.get_user_summary(today.isoformat())
        stats = summary.get('stats', summary)
        
        readiness_data['rhr'] = stats.get('restingHeartRate', 0)
        readiness_data['stress'] = stats.get('averageStressLevel', 0)
        
        bb_val = summary.get('stats_and_body', {}).get('bodyBatteryMostRecentValue')
        if bb_val is None: bb_val = stats.get('bodyBatteryMostRecentValue', 0)
        readiness_data['body_battery'] = bb_val
        
        readiness_data['sleep_seconds'] = stats.get('sleepingSeconds', 0)
        
        events = stats.get('bodyBatteryActivityEventList', [])
        for e in events:
            if e.get('eventType') == 'NAP':
                readiness_data['nap_seconds'] += e.get('durationInMilliseconds', 0) / 1000
                
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy Readiness: {e}")

    readiness_score = calculate_readiness_score(readiness_data)

    # --- B. Training Load (7 ngày) ---
    load_stats = {"avg_daily_load": 0, "final_calc_max_hr": 0, "raw_activities_for_ai": []}
    
    try:
        start_date = today - timedelta(days=DAYS_WINDOW - 1)
        activities = client.get_activities_by_date(start_date.isoformat(), today.isoformat(), "")
        
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
            
            if trimp > 5:
                load_stats['raw_activities_for_ai'].append(
                    f"- {date_str}: {name} ({int(duration_min)}p) | MaxHR {mx_hr} | TRIMP {int(trimp)}"
                )

        load_stats['avg_daily_load'] = total_trimp / DAYS_WINDOW
        load_stats['final_calc_max_hr'] = current_max_hr

    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy Load: {e}")

    return readiness_data, readiness_score, load_stats

# ==============================================================================
# 3. MODULE AI ANALYST (Giữ nguyên logic)
# ==============================================================================

def get_ai_advice(today, r_data, r_score, l_data, user_label="User"):
    print(f"[{user_label}] 🧠 Đang gọi AI Coach (Gemini)...")
    if not GEMINI_API_KEY:
        return "⚠️ Lỗi: Chưa cấu hình GEMINI_API_KEY."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        activities_text = "\n".join(l_data['raw_activities_for_ai']) if l_data['raw_activities_for_ai'] else "Không có hoạt động đáng kể."
        # Lấy thời gian hiện tại định dạng Giờ:Phút:Giây, Ngày/Tháng/Năm
        current_now = datetime.now().strftime("%H:%M:%S, %d/%m/%Y")

        prompt = f"""
        Bạn là Huấn luyện viên thể thao chuyên nghiệp (AI Running Coach).
        Hãy phân tích dữ liệu ngày {today} và đưa ra lời khuyên ngắn gọn cho VĐV tên {user_label}.
        Đây là thời gian hiện tại: {current_now}

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
        **Chỉ định:** [Nghỉ ngơi / Chạy nhẹ Zone 2 / Bài Interval...]
        **Chi tiết:** [Ví dụ: Chạy 30p pace 6:30 hoặc Nghỉ hoàn toàn]

        **💡 TIP PHỤC HỒI**
        [Một lời khuyên dinh cụ thể và khích lệ tinh thần cho VĐV.]
        """

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text

    except Exception as e:
        print(f"[{user_label}] ❌ Lỗi AI: {e}")
        return "AI Coach đang bận, vui lòng thử lại sau."

# ==============================================================================
# 4. MODULE TELEGRAM (Update: Nhận Chat ID động)
# ==============================================================================

async def send_telegram_report(message, chat_id, user_label="User"):
    print(f"[{user_label}] 📲 Đang gửi báo cáo qua Telegram...")
    if not TELE_TOKEN or not chat_id:
        print(f"[{user_label}] ⚠️ Chưa cấu hình Telegram Token/ID.")
        return

    bot = Bot(token=TELE_TOKEN)

    try:
        # CÁCH 1: Thử gửi với định dạng Markdown (để tin nhắn đẹp)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"[{user_label}] ✅ Đã gửi thành công (Markdown)!")
        
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi format Markdown: {e}")
        print(f"[{user_label}] 🔄 Đang chuyển sang gửi Plain Text...")
        
        try:
            # CÁCH 2 (FALLBACK): Gửi plain text nếu cách 1 lỗi
            # (Loại bỏ parse_mode để Telegram không check cú pháp)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
            print(f"[{user_label}] ✅ Đã gửi thành công (Plain Text)!")
            
        except Exception as e2:
            print(f"[{user_label}] ❌ Gửi thất bại hoàn toàn: {e2}")

# ==============================================================================
# 5. QUẢN LÝ LUỒNG ĐA NGƯỜI DÙNG (Multi-User Flow)
# ==============================================================================

async def process_single_user(user_config):
    """Xử lý toàn bộ quy trình cho 1 người dùng"""
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')
    tele_id = user_config.get('telegram_chat_id')

    if not email or not password:
        print(f"[{name}] ❌ Thiếu thông tin đăng nhập.")
        return

    try:
        # 1. Đăng nhập
        client = Garmin(email, password)
        client.login()
        print(f"[{name}] ✅ Đăng nhập Garmin thành công.")
        
        today = date.today()
        # today = date(2025, 12, 27) # Uncomment nếu muốn test ngày cũ

        # 2. Xử lý dữ liệu
        r_data, r_score, l_data = get_processed_data(client, today, name)

        # 3. AI Phân tích
        ai_report = get_ai_advice(today, r_data, r_score, l_data, name)

        # 4. Gửi Telegram
        if tele_id:
            await send_telegram_report(ai_report, tele_id, name)
        else:
            print(f"[{name}] ⚠️ Không có Telegram ID, bỏ qua bước gửi tin.")

    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý user: {e}")

async def main():
    print("=== GARMIN AI COACH PRO (MULTI-USER) ===")
    
    # Load danh sách user từ biến môi trường USERS_JSON
    users_json = os.getenv("USERS_JSON")
    
    if not users_json:
        print("❌ Lỗi: Không tìm thấy biến môi trường USERS_JSON.")
        print("Ví dụ format: USERS_JSON='[{\"name\": \"User1\", \"email\": \"...\", \"password\": \"...\", \"telegram_chat_id\": \"...\"}]'")
        return

    try:
        users = json.loads(users_json)
    except json.JSONDecodeError:
        print("❌ Lỗi: USERS_JSON không đúng định dạng JSON.")
        return

    if not users:
        print("⚠️ Danh sách user rỗng.")
        return

    print(f"🚀 Kích hoạt cho {len(users)} người dùng...")
    
    # Tạo danh sách các task để chạy song song
    tasks = [process_single_user(user) for user in users]
    
    # Chạy tất cả cùng lúc
    await asyncio.gather(*tasks)
    
    print("\n=== HOÀN TẤT ===")

if __name__ == "__main__":
    asyncio.run(main())