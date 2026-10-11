import math

def calculate_spo2_score(avg_spo2):
    """Tính điểm dựa trên nồng độ Oxy trong máu trung bình (0-100)"""
    if not avg_spo2: return None
    if avg_spo2 >= 95: return 100
    elif avg_spo2 >= 92: return 80
    elif avg_spo2 >= 90: return 60
    else: return 30

def calculate_resp_score(avg_sleep_resp):
    """Tính điểm dựa trên nhịp thở trung bình khi ngủ (0-100)"""
    if not avg_sleep_resp: return None
    # Nhịp thở lý tưởng khi ngủ thường từ 12-16 brpm
    if 12 <= avg_sleep_resp <= 16: return 100
    # Mức ổn định nhưng cần theo dõi
    elif 10 <= avg_sleep_resp < 12 or 16 < avg_sleep_resp <= 20: return 80
    # Dấu hiệu bất thường (quá chậm hoặc quá nhanh)
    else: return 40

def calculate_rhr_score(rhr):
    """Tính điểm dựa trên nhịp tim nghỉ (0-100).
    Dùng baseline mặc định 60 bpm. RHR càng thấp hơn baseline càng tốt,
    RHR tăng cao hơn baseline là dấu hiệu mệt mỏi/bệnh.
    """
    if not rhr or rhr < 30: return None  # Dữ liệu không hợp lệ
    BASELINE = 60
    diff = rhr - BASELINE
    if diff <= -10: return 100   # RHR <= 50: rất tốt
    elif diff <= -5: return 95   # RHR 51-55: tốt
    elif diff <= 0: return 90    # RHR 56-60: bình thường
    elif diff <= 5: return 75    # RHR 61-65: hơi cao
    elif diff <= 10: return 55   # RHR 66-70: cao
    elif diff <= 15: return 35   # RHR 71-75: cảnh báo
    else: return 15              # RHR > 75: nghiêm trọng

def calculate_hrv_score(hrv_status):
    """Ánh xạ trạng thái HRV sang điểm số (0-100)"""
    if not hrv_status: return None
    status_map = {
        "BALANCED": 100,
        "UNBALANCED": 50,
        "LOW": 30,
        "POOR": 10
    }
    return status_map.get(str(hrv_status).upper(), 70) # Default 70 cho trạng thái không xác định (vd: NO_STATUS)

def calculate_bb_score(bb_value):
    """Quy đổi Body Battery (0-100) sang điểm readiness (0-100).
    BB 50 trên Garmin là mức trung bình khá, cần được phản ánh đúng.
    """
    if not bb_value: return 0
    if bb_value >= 80: return 100
    elif bb_value >= 60: return 85
    elif bb_value >= 40: return 65
    elif bb_value >= 20: return 40
    else: return 15

def calculate_nap_bonus(nap_seconds):
    """Tính điểm bonus từ giấc ngủ trưa (0-10).
    Ngủ trưa 15-30 phút là lý tưởng, quá dài sẽ giảm hiệu quả.
    """
    if not nap_seconds or nap_seconds <= 0: return 0
    nap_min = nap_seconds / 60
    if 15 <= nap_min <= 30: return 10    # Lý tưởng
    elif 10 <= nap_min < 15: return 5    # Hơi ngắn
    elif 30 < nap_min <= 60: return 7    # Hơi dài nhưng vẫn tốt
    elif nap_min > 60: return 3          # Quá dài, sleep inertia
    else: return 0                       # Quá ngắn, không đáng kể

def calculate_readiness_score(data):
    """Tính điểm Sẵn sàng (0-100) dựa trên Sleep, Stress, BodyBattery, RHR, SpO2, Respiration, Nap."""
    # 1. Calculate Component Scores

    # --- Sleep ---
    hours_sleep = data.get('sleep_hours', 0)
    if hours_sleep < 5: sleep_score = 30
    elif hours_sleep < 6: sleep_score = 45
    elif hours_sleep < 6.5: sleep_score = 55
    elif hours_sleep < 7: sleep_score = 70
    elif hours_sleep < 7.5: sleep_score = 85
    elif hours_sleep <= 9: sleep_score = 100
    elif hours_sleep <= 9.5: sleep_score = 90
    else: sleep_score = 75  # Ngủ quá nhiều (> 9.5h) cũng không tốt

    # --- Stress (thang mượt hơn) ---
    avg_stress = data.get('stress', 50)
    if avg_stress <= 25: stress_score = 100
    elif avg_stress <= 30: stress_score = 90
    elif avg_stress <= 35: stress_score = 80
    elif avg_stress <= 40: stress_score = 65
    elif avg_stress <= 50: stress_score = 50
    elif avg_stress <= 60: stress_score = 35
    else: stress_score = 20

    # --- Body Battery (quy đổi lại cho công bằng) ---
    bb_raw = data.get('body_battery', 0)
    if not bb_raw: bb_raw = 0
    bb_score = calculate_bb_score(bb_raw)

    # --- RHR ---
    rhr = data.get('rhr', 0)
    rhr_score = calculate_rhr_score(rhr)

    # --- SpO2 & Respiration ---
    spo2_val = data.get('avg_spo2')
    spo2_score = calculate_spo2_score(spo2_val)

    resp_val = data.get('avg_sleep_resp')
    resp_score = calculate_resp_score(resp_val)

    # --- HRV ---
    hrv_status = data.get('hrv_status')
    hrv_score = calculate_hrv_score(hrv_status)

    # --- Nap Bonus ---
    nap_sec = data.get('nap_seconds', 0)
    nap_bonus = calculate_nap_bonus(nap_sec)

    # 2. Define Weights (tổng = 1.0)
    w_sleep = 0.25
    w_bb = 0.20
    w_stress = 0.20
    w_hrv = 0.10
    w_rhr = 0.10
    w_spo2 = 0.08
    w_resp = 0.07

    # 3. Dynamic Weight Redistribution (khi thiếu dữ liệu)
    has_hrv = hrv_score is not None
    has_rhr = rhr_score is not None
    has_spo2 = spo2_score is not None
    has_resp = resp_score is not None

    # Thu thập trọng số bị mất
    lost_weight = 0
    if not has_hrv:
        lost_weight += w_hrv
        w_hrv = 0
    if not has_rhr:
        lost_weight += w_rhr
        w_rhr = 0
    if not has_spo2:
        lost_weight += w_spo2
        w_spo2 = 0
    if not has_resp:
        lost_weight += w_resp
        w_resp = 0

    # Phân bổ đều trọng số bị mất cho 3 chỉ số chính
    if lost_weight > 0:
        bonus = lost_weight / 3
        w_sleep += bonus
        w_bb += bonus
        w_stress += bonus

    # 4. Calculate Final Score
    safe_hrv = hrv_score if has_hrv else 0
    safe_rhr = rhr_score if has_rhr else 0
    safe_spo2 = spo2_score if has_spo2 else 0
    safe_resp = resp_score if has_resp else 0

    weighted_score = (w_sleep * sleep_score) + \
                     (w_bb * bb_score) + \
                     (w_stress * stress_score) + \
                     (w_hrv * safe_hrv) + \
                     (w_rhr * safe_rhr) + \
                     (w_spo2 * safe_spo2) + \
                     (w_resp * safe_resp)

    # Cộng Nap Bonus (tối đa 10 điểm, không vượt 100)
    final_score = min(weighted_score + nap_bonus, 100)

    # Phạt nặng nếu Pin cơ thể quá thấp
    if bb_raw < 20:
        final_score = min(final_score, 30)

    # Phạt nếu RHR tăng đột biến (> 75 bpm)
    if rhr and rhr > 75:
        final_score = min(final_score, 40)

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
