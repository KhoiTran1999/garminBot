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

def calculate_readiness_score(data):
    """Tính điểm Sẵn sàng (0-100) dựa trên Sleep, Stress, BodyBattery, SpO2, Respiration"""
    # 1. Calculate Component Scores
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
    if not bb_score: bb_score = 0
    
    spo2_val = data.get('avg_spo2')
    spo2_score = calculate_spo2_score(spo2_val)

    resp_val = data.get('avg_sleep_resp')
    resp_score = calculate_resp_score(resp_val)
    
    # 2. Define Weights
    w_sleep = 0.3
    w_bb = 0.3
    w_stress = 0.2
    w_spo2 = 0.1
    w_resp = 0.1
    
    # 3. Dynamic Weight Redistribution
    has_spo2 = spo2_score is not None
    has_resp = resp_score is not None
    
    if has_spo2 and has_resp:
        # Full data
        pass
    elif not has_spo2 and has_resp:
        # Missing SpO2 -> Transfer weight to Resp
        w_spo2 = 0
        w_resp = 0.2
    elif has_spo2 and not has_resp:
         # Missing Resp -> Transfer weight to SpO2
         w_resp = 0
         w_spo2 = 0.2
    else:
        # Missing Both -> Return to original formulation (Sleep 0.4, BB 0.4)
        w_spo2 = 0
        w_resp = 0
        w_sleep = 0.4
        w_bb = 0.4
        
    # 4. Calculate Final Score
    # Use 0 for missing scores to avoid NoneType error calculation, 
    # but their weight is 0 so it won't affect result.
    safe_spo2 = spo2_score if has_spo2 else 0
    safe_resp = resp_score if has_resp else 0
    
    weighted_score = (w_sleep * sleep_score) + \
                     (w_bb * bb_score) + \
                     (w_stress * stress_score) + \
                     (w_spo2 * safe_spo2) + \
                     (w_resp * safe_resp)
    
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
