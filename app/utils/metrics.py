import math

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
