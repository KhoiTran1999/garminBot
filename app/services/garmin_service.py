from datetime import timedelta, datetime, date
import pytz
from app.utils.metrics import calculate_readiness_score, calculate_trimp_banister, seconds_to_text

# Cấu hình cửa sổ quét (7 ngày cho Acute Load)
DAYS_WINDOW = 7

def check_garmin_sync_status(client, max_age_hours=1.0, user_label="User"):
    """
    Kiểm tra xem thiết bị có được sync trong khoảng thời gian cho phép hay không.
    Trả về: (is_fresh: bool, message: str)
    """
    print(f"[{user_label}] ⌚ Checking device sync freshness (Max Age: {max_age_hours}h)...")
    
    last_sync_ts = 0
    device_name = "Unknown Device"
    source = "None"

    # --- CÁCH 1: Check Last Used Device (Ưu tiên số 1) ---
    try:
        last_used = client.get_device_last_used()
        if last_used:
            last_sync_ts = last_used.get("lastUsedDeviceUploadTime", 0)
            if last_sync_ts > 0: last_sync_ts = last_sync_ts / 1000
            device_name = last_used.get("lastUsedDeviceName") or last_used.get("deviceName")
            source = "LastUsed"
    except Exception as e:
        print(f"[{user_label}] ⚠️ Check Last Used Error: {e}")

    # --- CÁCH 2: Check User Summary (Fallback) ---
    if last_sync_ts == 0:
        try:
            today_iso = date.today().isoformat()
            summary = client.get_user_summary(today_iso)
            last_sync_ts = summary.get("lastSyncTimestampGMT", 0)
            if last_sync_ts > 0: last_sync_ts = last_sync_ts / 1000
            source = "UserSummary"
        except Exception:
            pass

    # --- EVALUATE ---
    if last_sync_ts == 0:
        return False, "Không tìm thấy dữ liệu đồng bộ nào."

    # Convert timestamps
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    last_sync_dt = datetime.fromtimestamp(last_sync_ts, vn_tz)
    now_vn = datetime.now(vn_tz)
    
    diff = now_vn - last_sync_dt
    diff_hours = diff.total_seconds() / 3600
    
    time_str = last_sync_dt.strftime("%H:%M %d/%m")
    
    if diff_hours <= max_age_hours:
        return True, f"✅ Data synced {time_str} ({int(diff_hours*60)} min ago)."
    else:
        return False, f"⚠️ Dữ liệu cũ (Sync lúc {time_str} - {int(diff_hours)}h trước). Vui lòng mở App Garmin Connect để đồng bộ."

def get_sleep_analysis(client, date_str, user_label="User"):
    """
    Lấy dữ liệu giấc ngủ chi tiết (Deep, Light, REM) và tạo text cho AI.
    Trả về: (real_sleep_hours, sleep_description_text)
    """
    try:
        sleep_data = client.get_sleep_data(date_str)
        dto = sleep_data.get('dailySleepDTO', {})
        
        if not dto:
            return 0, "Không có dữ liệu giấc ngủ chi tiết (Chưa đồng bộ)."

        deep = dto.get('deepSleepSeconds') or 0
        light = dto.get('lightSleepSeconds') or 0
        rem = dto.get('remSleepSeconds') or 0
        awake = dto.get('awakeSleepSeconds') or 0
        
        # Tính tổng ngủ THỰC TẾ (Không tính Awake)
        real_sleep_sec = deep + light + rem
        real_sleep_hours = real_sleep_sec / 3600

        sleep_text = (
            f"Tổng ngủ thực: {seconds_to_text(real_sleep_sec)} (đã trừ lúc thức).\n"
            f"   - Ngủ sâu (Deep): {seconds_to_text(deep)}\n"
            f"   - Ngủ nông (Light): {seconds_to_text(light)}\n"
            f"   - Ngủ mơ (REM): {seconds_to_text(rem)}\n"
            f"   - Thời gian thức: {seconds_to_text(awake)}"
        )
        return real_sleep_hours, sleep_text

    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy chi tiết giấc ngủ: {e}")
        return 0, "Không lấy được chi tiết giấc ngủ."

def get_processed_data(client, today, user_label="User"):
    print(f"[{user_label}] 🔄 Đang thu thập dữ liệu Garmin...")
    
    readiness_data = {
        "rhr": 0, "stress": 0, "body_battery": 0, 
        "sleep_hours": 0, "nap_seconds": 0, "sleep_text": "Chưa có dữ liệu"
    }
    date_iso = today.isoformat()

    # --- A. Lấy chỉ số cơ bản ---
    try:
        summary = client.get_user_summary(date_iso)
        stats = summary.get('stats', summary)
        
        # Handle None values explicitly using 'or 0'
        readiness_data['rhr'] = stats.get('restingHeartRate') or 0
        readiness_data['stress'] = stats.get('averageStressLevel') or 0
        
        bb_val = summary.get('stats_and_body', {}).get('bodyBatteryMostRecentValue')
        if bb_val is None: bb_val = stats.get('bodyBatteryMostRecentValue') or 0
        readiness_data['body_battery'] = bb_val
        
        events = stats.get('bodyBatteryActivityEventList') or []
        if events:
            for e in events:
                if e.get('eventType') == 'NAP':
                    readiness_data['nap_seconds'] += (e.get('durationInMilliseconds') or 0) / 1000
                
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy User Summary: {e}")

    # --- B. Phân tích giấc ngủ sâu ---
    real_hours, sleep_desc = get_sleep_analysis(client, date_iso, user_label)
    readiness_data['sleep_hours'] = real_hours
    readiness_data['sleep_text'] = sleep_desc

    # --- B2. SpO2 & Respiration ---
    try:
        # SpO2
        spo2_data = get_spo2_data(client, date_iso) or {}
        readiness_data['avg_spo2'] = spo2_data.get('averageSpO2')
        readiness_data['min_spo2'] = spo2_data.get('lowestSpO2')
        readiness_data['last_spo2'] = spo2_data.get('latestSpO2')

        # Respiration
        resp_data = get_respiration_data(client, date_iso) or {}
        readiness_data['avg_waking_resp'] = resp_data.get('avgWakingRespirationValue')
        readiness_data['avg_sleep_resp'] = resp_data.get('avgSleepRespirationValue')
        readiness_data['min_resp'] = resp_data.get('lowestRespirationValue')
        readiness_data['max_resp'] = resp_data.get('highestRespirationValue')
        
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy SpO2/Respiration: {e}")

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
            
            if trimp > 10: 
                load_stats['raw_activities_for_ai'].append(
                    f"- {date_str}: {name} ({int(duration_min)}p) | MaxHR {mx_hr} | TRIMP {int(trimp)}"
                )

        load_stats['avg_daily_load'] = total_trimp / DAYS_WINDOW
        load_stats['final_calc_max_hr'] = current_max_hr

    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi lấy Activities: {e}")

    return readiness_data, readiness_score, load_stats

def fetch_daily_activities_detailed(client, date_obj, user_label="User"):
    """
    Lấy danh sách hoạt động trong ngày (Hôm nay) kèm detail full.
    Trả về list các dict activity_details.
    """
    print(f"[{user_label}] 🔄 Đang quét hoạt động trong ngày...")
    
    # Only fetch today's activities
    start_date = date_obj 
    
    try:
        activities = client.get_activities_by_date(start_date.isoformat(), date_obj.isoformat(), "")
        
        if not activities:
            print(f"[{user_label}] ⚠️ Không có hoạt động nào trong ngày.")
            return []

        detailed_list = []
        print(f"[{user_label}] ✅ Tìm thấy {len(activities)} hoạt động. Đang lấy chi tiết...")

        for act in activities:
            activity_id = act.get("activityId")
            activity_name = act.get("activityName")
            
            # Base structure
            detail_obj = {
                "activityId": activity_id,
                "activityName": activity_name,
                "summary": act
            }

            # Helper to safely call API
            def safe_fetch(method_name, key):
                try:
                    method = getattr(client, method_name)
                    data = method(activity_id)
                    detail_obj[key] = data
                except Exception:
                    detail_obj[key] = None

            # Fetch deep details
            safe_fetch("get_activity_splits", "splits")
            safe_fetch("get_activity_weather", "weather")
            safe_fetch("get_activity_hr_in_timezones", "hr_zones")
            safe_fetch("get_activity_power_in_timezones", "power_zones")
            safe_fetch("get_activity_details", "activity_details") # Time-series data

            detailed_list.append(detail_obj)
            
        return detailed_list

    except Exception as e:
        print(f"[{user_label}] ❌ Lỗi fetch activity detailed: {e}")
        return []

def get_spo2_data(client, date_str):
    """
    Lay du lieu SpO2 trong ngay.
    """
    try:
        return client.get_spo2_data(date_str)
    except Exception as e:
        print(f"⚠️ Lỗi lấy SpO2: {e}")
        return None

def get_respiration_data(client, date_str):
    """
    Lay du lieu Respiration (Nhip tho) trong ngay.
    """
    try:
        return client.get_respiration_data(date_str)
    except Exception as e:
        print(f"⚠️ Lỗi lấy Respiration: {e}")
        return None

def get_hrv_data(client, date_str):
    """
    Lay du lieu HRV (Heart Rate Variability) trong ngay.
    """
    try:
        return client.get_hrv_data(date_str)
    except Exception as e:
        print(f"⚠️ Lỗi lấy HRV: {e}")
        return None
