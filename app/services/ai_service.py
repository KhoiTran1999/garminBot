import os
import json
import pytz
import time
import struct
import random
from datetime import datetime
from typing import Optional, Dict
from google import genai
from google.genai import types
from app.config import Config
from app.services.redis_service import redis_service

class GeminiKeyManager:
    """
    Quản lý danh sách API Key Gemini cho TTS
    """
    def __init__(self):
        self.keys = []
        self._load_keys()
        self.current_index = 0

    def _load_keys(self):
        self.keys = Config.GEMINI_API_KEYS
        print(f"Loaded {len(self.keys)} Gemini Keys from Config.")

    def get_current_key(self):
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate_key(self):
        if not self.keys:
            return None
        self.current_index = (self.current_index + 1) % len(self.keys)
        return self.get_current_key()

    def get_key_count(self):
        return len(self.keys)

    def execute_with_retry(self, worker_func, default_return=None, verbose_label="Service"):
        max_attempts = self.get_key_count() * 2
        if max_attempts == 0:
            print(f"[{verbose_label}] Warning: No API Keys available to execute.")
            return default_return

        for attempt in range(max_attempts):
            current_api_key = self.get_current_key()
            try:
                result = worker_func(current_api_key)
                self.rotate_key()
                return result

            except Exception as e:
                error_msg = str(e)
                print(f"[{verbose_label}] Error (Key ...{current_api_key[-5:] if current_api_key else 'None'}): {error_msg}")

                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                    self.rotate_key()
                    time.sleep(1)
                else:
                    self.rotate_key()
                    time.sleep(2)

        return default_return

import requests
from openai import OpenAI

def call_ai_api(api_key, model_name, prompt):
    client = OpenAI(
        base_url="https://khoitran1999-claude-server.hf.space/v1",
        api_key=api_key
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )

    content = response.choices[0].message.content
    if not content:
        raise Exception("Empty response from AI model")
    return content

# Khởi tạo Global Instance
gemini_key_manager = GeminiKeyManager()


def get_ai_advice(today, r_data, r_score, l_data, user_config, prompt_template=None, mode="daily", aqi_data=None):
    """
    Gọi AI để lấy lời khuyên. Tự động xoay key khi gặp lỗi Quota.
    """
    # Lấy thông tin cá nhân hóa từ Notion
    user_label = user_config.get('name', 'VĐV')
    email = user_config.get('email')
    goal = user_config.get('goal', 'Duy trì sức khỏe')
    injury = user_config.get('injury', 'Không có')
    note = user_config.get('note', '')

    # Fetch recent AI reports for context
    recent_reports = redis_service.get_ai_context(email, mode)
    context_str = ""
    if recent_reports:
        context_str = "\n\n*** 📝 LỊCH SỬ BÁO CÁO CỦA CÁC NGÀY TRƯỚC (Dùng tham khảo xu hướng) ***\n"
        for idx, rep in enumerate(recent_reports, 1):
            context_str += f"\n-- Báo cáo {idx} --\n{rep}\n"
        context_str += "\n*****************************************************************\n"

    print(f"[{user_label}] Calling AI Coach (Mode: {mode} | Context: {goal})...")
    
    # Chuẩn bị Prompt
    activities_text = "\n".join(l_data['raw_activities_for_ai']) if l_data['raw_activities_for_ai'] else "Không có hoạt động đáng kể."
    vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    current_now = datetime.now(vn_timezone).strftime("%H:%M:%S, %d/%m/%Y")
    nap_text = f"+ Ngủ trưa: {int(r_data['nap_seconds']//60)} phút" if r_data['nap_seconds'] > 0 else ""
    
    spo2_text = "Không có dữ liệu"
    if r_data.get('avg_spo2'):
        spo2_text = f"Avg {int(r_data['avg_spo2'])}% | Min {int(r_data['min_spo2'])}% | Last {int(r_data['last_spo2'])}%"
    
    resp_text = "Không có dữ liệu"
    if r_data.get('avg_waking_resp'):
        resp_text = (f"Waking Avg {int(r_data['avg_waking_resp'])} brpm | Sleep Avg {int(r_data['avg_sleep_resp'])} brpm | "
                        f"Min {int(r_data['min_resp'])} - Max {int(r_data['max_resp'])}")

    hrv_text = "Không có dữ liệu"
    if r_data.get('hrv_status'):
        hrv_text = f"Status: {r_data.get('hrv_status', 'N/A')} | Last Night: {r_data.get('last_night_hrv', 'N/A')} ms"

    training_status_text = "Không có dữ liệu"
    if r_data.get('training_status'):
        training_status_text = r_data.get('training_status')

    timeseries_text = r_data.get('timeseries_text', "Không có dữ liệu")

    # AQI Data
    aqi_text = "Không có dữ liệu"
    if aqi_data:
        aqi_text = f"AQI: {aqi_data.get('aqi', 'N/A')} | PM2.5: {aqi_data.get('pm25', 'N/A')} (Location: {aqi_data.get('city', 'Unknown')})"

    
    # Pre-calculate derived values for safe formatting
    avg_daily_load_int = int(l_data['avg_daily_load']) if l_data and 'avg_daily_load' in l_data else 0

    formatted_prompt = None
    default_model = Config.MODEL_WORKER
    model_to_use = default_model

    if prompt_template and isinstance(prompt_template, dict):
        try:
            # New structure: system_prompt, user_template, model
            sys_p = prompt_template.get("system_prompt", "")
            user_tmplt = prompt_template.get("user_template", "")
            model_to_use = prompt_template.get("model", default_model)
            
            # Format User Template only (System Prompt is usually static or minimal)
            # If system prompt specifically needs formatting, add it here.
            # Assuming currently only user_template needs dynamic data.
            formatted_user_part = user_tmplt.format(
                user_label=user_label,
                goal=goal,
                injury=injury,
                note=note,
                current_now=current_now,
                r_score=r_score,
                r_data=r_data,
                l_data=l_data,
                avg_daily_load_int=avg_daily_load_int,
                activities_text=activities_text,
                nap_text=nap_text,
                spo2_text=spo2_text,
                resp_text=resp_text,
                hrv_text=hrv_text,
                training_status_text=training_status_text,
                timeseries_text=timeseries_text,
                aqi_info=aqi_text
            )
            
            # Concatenate System + User. Or better: keep them separate if API supports. 
            # But generate_content usually takes string or list.
            # Let's combine them for simplicity:
            formatted_prompt = f"{sys_p}\n\n{formatted_user_part}"

        except Exception as e:
            print(f"[{user_label}] Error formatting Notion prompt ({mode}): {e}")
            formatted_prompt = None
    elif prompt_template and isinstance(prompt_template, str):
         # Old behavior / Fallback if string passed
         try:
            formatted_prompt = prompt_template.format(
                user_label=user_label,
                goal=goal,
                injury=injury,
                note=note,
                current_now=current_now,
                r_score=r_score,
                r_data=r_data,
                l_data=l_data,
                avg_daily_load_int=avg_daily_load_int,
                activities_text=activities_text,
                nap_text=nap_text,
                spo2_text=spo2_text,
                resp_text=resp_text,
                hrv_text=hrv_text,
                training_status_text=training_status_text,
                timeseries_text=timeseries_text,
                aqi_info=aqi_text
            )
         except Exception as e:
            print(f"[{user_label}] Error formatting Notion string prompt ({mode}): {e}")
            formatted_prompt = None

    if formatted_prompt:
        prompt = formatted_prompt
    elif mode == "sleep_analysis":
        prompt = f"""
        Bạn là Chuyên gia giấc ngủ và Hiệu suất thể thao (AI Sleep Coach).
        Hãy phân tích dữ liệu giấc ngủ đêm qua và đưa ra lời khuyên đầu ngày cho: {user_label}.
        Thời gian báo cáo hiện tại: {current_now}

        HỒ SƠ VĐV:
        - **Mục tiêu:** {goal}
        - **Chấn thương:** {injury}
        - **Lưu ý:** {note}

        DỮ LIỆU ĐÊM QUA & SÁNG NAY:
        - **Điểm Sẵn sàng (Readiness):** {r_score}/100
        - **Giấc ngủ:** {r_data['sleep_text']} (Ngủ nông/sâu/REM)
        - **Phục hồi:** Body Battery {r_data['body_battery']}/100 | Stress {r_data['stress']}
        - **Nhịp tim nghỉ (RHR):** {r_data['rhr']} bpm
        - **HRV (Biến thiên nhịp tim):** {hrv_text}
        - **SpO2 (Oxy máu):** {spo2_text}
        - **Hô hấp (Respiration):** {resp_text}
        - **Trạng thái tập luyện (Training Status):** {training_status_text}
        - **Chất lượng không khí (AQI):** {aqi_text}

        BIẾN ĐỘNG TRONG NGÀY (2-hour blocks):
{timeseries_text}

        YÊU CẦU OUTPUT (Markdown Telegram):
        Trả về báo cáo ngắn gọn, tập trung vào chất lượng giấc ngủ và sự sẵn sàng cho ngày mới:

        **💤 PHÂN TÍCH GIẤC NGỦ**
        [Đánh giá chất lượng giấc ngủ đêm qua: Sâu/REM có đủ không? Có bị thức giấc nhiều không?]
        [Nhận xét về SpO2 và Nhịp thở nếu có bất thường]

        **🔋 TRẠNG THÁI PHỤC HỒI**
        [Dựa trên Body Battery và Stress, cơ thể đã nạp đủ năng lượng chưa?]

        **🌅 LỜI KHUYÊN SÁNG NAY**
        [Lời khuyên để có một ngày tốt lành.]

        LƯU Ý: 
        Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách.
        """
    else:
        prompt = f"""
        Bạn là Huấn luyện viên thể thao chuyên nghiệp (AI Running Coach).
        Hãy phân tích dữ liệu và đưa ra giáo án cho VĐV: {user_label}.
        Thời gian báo cáo hiện tại: {current_now}

        HỒ SƠ VĐV:
        - **Mục tiêu hiện tại:** {goal}
        - **Tình trạng chấn thương/Bệnh lý:** {injury}
        - **Ghi chú thêm:** {note}

        DỮ LIỆU CƠ THỂ HÔM NAY:
        - **Điểm Sẵn sàng:** {r_score}/100
        - **Cơ thể:** Pin Body Battery {r_data['body_battery']}/100 | Stress {r_data['stress']} (Thấp <25, Cao >50)
        - **Giấc ngủ:** {r_data['sleep_text']}
            {nap_text}
        - **Nhịp tim nghỉ (RHR):** {r_data['rhr']} bpm
        - **HRV (Biến thiên nhịp tim):** {hrv_text}
        - **Trạng thái tập luyện (Training Status):** {training_status_text}
        - **SpO2:** {spo2_text}
        - **Hô hấp:** {resp_text}
        - **AQI (Không khí):** {aqi_text}

        BIẾN ĐỘNG TRONG NGÀY (2-hour blocks):
{timeseries_text}

        TẢI TẬP LUYỆN (7 NGÀY):
        - **Tải trung bình ngày (Acute Load):** {int(l_data['avg_daily_load'])} (TRIMP Index)
        - **Lịch sử hoạt động:**
        {activities_text}

        YÊU CẦU OUTPUT (Markdown Telegram):
        Trả về báo cáo theo format dưới đây, văn phong thân thiện nhưng chuyên môn:

        **🔢 TỔNG QUAN HÔM NAY**
        [Tổng hợp các chỉ số hiện tại của cơ thể và giấc ngủ.]

        **🔥 ĐÁNH GIÁ TRẠNG THÁI**
        [Cơ thể đang Sung sức hay Mệt mỏi? Giấc ngủ và Stress ảnh hưởng thế nào?]

        **🏃 BÀI TẬP ĐỀ XUẤT**
        [Dựa trên điểm Sẵn sàng và Tải tập luyện, đề xuất có nên tập hay nghỉ ngơi. Nếu tập, gợi ý cường độ và loại bài tập phù hợp.]

        **💡 LỜI KHUYÊN**
        [Một lời khuyên về dinh dưỡng hoặc phục hồi phù hợp với goal hiện tại.]

        LƯU Ý: Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách.
        """

    # Append AI context to prompt
    if context_str:
        prompt += context_str

    # --- GỌI API TRỰC TIẾP (Không Retry Key) ---
    try:
        if Config.ROUTER9_API_KEY:
            ai_report = call_ai_api(Config.ROUTER9_API_KEY, model_to_use, prompt)
            if ai_report and email:
                report_with_time = f"--- [Thời gian báo cáo: {current_now}] ---\n{ai_report}"
                redis_service.save_ai_context(email, mode, report_with_time)
            return ai_report
        else:
             print(f"[{user_label}] ROUTER9_API_KEY not found.")
             return "AI Coach chưa được cấu hình ROUTER9_API_KEY."
    except Exception as e:
        print(f"[{user_label}] AI Error: {str(e)}")
        return "AI Coach đang bận hoặc gặp lỗi. Vui lòng thử lại sau."

def get_battery_analysis_advice(today, r_data, user_config, prompt_template=None, aqi_data=None):
    """
    Gọi AI để phân tích năng lượng (Body Battery & Stress) trong ngày.
    """
    user_label = user_config.get('name', 'VĐV')
    email = user_config.get('email')
    goal = user_config.get('goal', 'Duy trì sức khỏe')

    print(f"[{user_label}] Calling AI Coach (Mode: battery)...")

    # Fetch recent AI reports for context
    mode = "battery"
    recent_reports = redis_service.get_ai_context(email, mode)
    context_str = ""
    if recent_reports:
        context_str = "\n\n*** 📝 LỊCH SỬ BÁO CÁO CỦA CÁC NGÀY TRƯỚC (Dùng tham khảo xu hướng) ***\n"
        for idx, rep in enumerate(recent_reports, 1):
            context_str += f"\n-- Báo cáo {idx} --\n{rep}\n"
        context_str += "\n*****************************************************************\n"

    vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    current_now = datetime.now(vn_timezone).strftime("%H:%M:%S, %d/%m/%Y")

    timeseries_text = r_data.get('timeseries_text', "Không có dữ liệu")
    body_battery = r_data.get('body_battery', 0)
    stress = r_data.get('stress', 0)

    aqi_text = "Không có dữ liệu"
    if aqi_data:
        aqi_text = f"AQI: {aqi_data.get('aqi', 'N/A')} | PM2.5: {aqi_data.get('pm25', 'N/A')} (Location: {aqi_data.get('city', 'Unknown')})"

    formatted_prompt = None
    default_model = Config.MODEL_WORKER
    model_to_use = default_model

    if prompt_template and isinstance(prompt_template, dict):
        try:
            sys_p = prompt_template.get("system_prompt", "")
            user_tmplt = prompt_template.get("user_template", "")
            model_to_use = prompt_template.get("model", default_model)

            formatted_user_part = user_tmplt.format(
                user_label=user_label,
                goal=goal,
                current_now=current_now,
                body_battery=body_battery,
                stress=stress,
                timeseries_text=timeseries_text,
                aqi_info=aqi_text
            )
            formatted_prompt = f"{sys_p}\n\n{formatted_user_part}"
        except Exception as e:
            print(f"[{user_label}] Error formatting Notion prompt (battery): {e}")
            formatted_prompt = None
    elif prompt_template and isinstance(prompt_template, str):
         try:
            formatted_prompt = prompt_template.format(
                user_label=user_label,
                goal=goal,
                current_now=current_now,
                body_battery=body_battery,
                stress=stress,
                timeseries_text=timeseries_text,
                aqi_info=aqi_text
            )
         except Exception as e:
            print(f"[{user_label}] Error formatting Notion string prompt (battery): {e}")
            formatted_prompt = None

    if formatted_prompt:
        prompt = formatted_prompt
    else:
        prompt = f"""
        Bạn là Huấn luyện viên và Chuyên gia sức khỏe (AI Energy Coach).
        Hãy phân tích xu hướng Pin cơ thể (Body Battery) và Căng thẳng (Stress) trong ngày của: {user_label}.
        Thời gian báo cáo hiện tại: {current_now}

        MỤC TIÊU VĐV: {goal}

        DỮ LIỆU HIỆN TẠI:
        - **Pin cơ thể (Body Battery):** {body_battery}/100
        - **Căng thẳng (Stress) trung bình:** {stress} (Thấp <25, Cao >50)
        - **Chất lượng không khí (AQI):** {aqi_text}

        BIẾN ĐỘNG TRONG NGÀY (2-hour blocks):
{timeseries_text}

        YÊU CẦU OUTPUT (Markdown Telegram):
        Trả về báo cáo phân tích biểu đồ năng lượng, tập trung tìm ra nguyên nhân hao hụt pin:

        **🔋 TRẠNG THÁI NĂNG LƯỢNG**
        [Đánh giá tổng quan mức pin hiện tại có ổn không?]

        **📉 PHÂN TÍCH TIÊU HAO & PHỤC HỒI**
        [Dựa vào Biến động trong ngày, chỉ ra khung giờ nào tụt pin nhiều nhất. Nếu có tập thể dục (Tập: ...), hãy nói rõ hao pin do tập là tốt. Nếu tụt pin do Stress cao mà không tập, hãy nhắc nhở.]

        **💡 LỜI KHUYÊN NĂNG LƯỢNG**
        [Lời khuyên để phục hồi pin nhanh nhất trong phần còn lại của ngày.]

        LƯU Ý: Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách.
        """

    # Append AI context to prompt
    if context_str:
        prompt += context_str

    try:
        if Config.ROUTER9_API_KEY:
            ai_report = call_ai_api(Config.ROUTER9_API_KEY, model_to_use, prompt)
            if ai_report and email:
                report_with_time = f"--- [Thời gian báo cáo: {current_now}] ---\n{ai_report}"
                redis_service.save_ai_context(email, mode, report_with_time)
            return ai_report
        else:
             print(f"[{user_label}] ROUTER9_API_KEY not found.")
             return "AI Coach chưa được cấu hình ROUTER9_API_KEY."
    except Exception as e:
        print(f"[{user_label}] AI Error: {str(e)}")
        return "AI Coach đang bận hoặc gặp lỗi. Vui lòng thử lại sau."
def get_workout_analysis_advice(activity_data_list, user_config, prompt_template=None, aqi_data=None):
    """
    Phân tích chi tiết (Time-series) các bài tập trong 24h.
    """
    user_label = user_config.get('name', 'VĐV')
    email = user_config.get('email')
    goal = user_config.get('goal', 'Cải thiện thành tích')

    print(f"[{user_label}] Analyzing workout details...")

    if not activity_data_list:
        return None

    # Fetch recent AI reports for context
    mode = "workout"
    recent_reports = redis_service.get_ai_context(email, mode)
    context_str = ""
    if recent_reports:
        context_str = "\n\n*** 📝 LỊCH SỬ BÁO CÁO CỦA CÁC NGÀY TRƯỚC (Dùng tham khảo xu hướng) ***\n"
        for idx, rep in enumerate(recent_reports, 1):
            context_str += f"\n-- Báo cáo {idx} --\n{rep}\n"
        context_str += "\n*****************************************************************\n"

    # Serialization
    import json
    activities_json = json.dumps(activity_data_list, ensure_ascii=False, default=str)
    
    vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    current_now = datetime.now(vn_timezone).strftime("%H:%M:%S, %d/%m/%Y")

    # AQI Data
    aqi_text = "Không có dữ liệu"
    if aqi_data:
        aqi_text = f"AQI: {aqi_data.get('aqi', 'N/A')} | PM2.5: {aqi_data.get('pm25', 'N/A')} (Location: {aqi_data.get('city', 'Unknown')})"

    formatted_prompt = None
    default_model = Config.MODEL_WORKER
    model_to_use = default_model

    if prompt_template and isinstance(prompt_template, dict):
        try:
            sys_p = prompt_template.get("system_prompt", "")
            user_tmplt = prompt_template.get("user_template", "")
            model_to_use = prompt_template.get("model", default_model)

            formatted_user = user_tmplt.format(
                user_label=user_label,
                goal=goal,
                current_now=current_now,
                activities_json=activities_json,
                aqi_info=aqi_text
            )
            formatted_prompt = f"{sys_p}\n\n{formatted_user}"
        except Exception as e:
             print(f"[{user_label}] Error formatting Notion workout prompt (dict): {e}")
             formatted_prompt = None

    elif prompt_template and isinstance(prompt_template, str):
        try:
            formatted_prompt = prompt_template.format(
                user_label=user_label,
                goal=goal,
                current_now=current_now,
                activities_json=activities_json,
                aqi_info=aqi_text
            )
        except Exception as e:
            print(f"[{user_label}] Error formatting Notion workout prompt: {e}")
            formatted_prompt = None

    if formatted_prompt:
        prompt = formatted_prompt
    else:
        prompt = f"""
        Bạn là Chuyên gia phân tích dữ liệu thể thao (Sports Data Scientist) và HLV chuyên nghiệp.
        Hãy phân tích dữ liệu bài tập trong 24h qua của VĐV: {user_label}.
        Thời gian báo cáo: {current_now}
        
        MỤC TIÊU VĐV: {goal}
        THÔNG TIN MÔI TRƯỜNG (AQI): {aqi_text}
        
        DỮ LIỆU CHI TIẾT (JSON):
        {activities_json}
        
        YÊU CẦU PHÂN TÍCH (Time-series Analysis):
        Dựa vào Splits, HR Zones, Power Zones, Weather và Activity Details:
        1. **Phân tích Biểu đồ & Splits:**
            - Pace/Power có ổn định không? Có bị drift (trượt) nhịp tim không (Cardiac Drift)?
            - Phân bổ sức (Pacing strategy) trong các splits như thế nào (Negative, Positive, hay Even Split)?
        2. **Đánh giá Cường độ & Hiệu quả:**
            - Thời gian trong các vùng tim (HR Zones) và vùng Power có phù hợp với loại bài tập không?
            - Tác động của thời tiết (Nhiệt độ, Gió) lên hiệu suất.
        3. **Nhận xét & Lời khuyên:**
            - Kỹ thuật/Chiến thuật cần cải thiện.
            - Đánh giá bài tập này đóng góp gì cho mục tiêu {goal}.
        
        OUTPUT FORMAT (Markdown Telegram):
        Trả về báo cáo ngắn gọn, chuyên sâu, dùng emoji:
        
        **📊 PHÂN TÍCH BÀI TẬP CHUYÊN SÂU**
        
        **1. 🏃 Đánh giá Pace & Chiến thuật**
        [Nhận xét về độ ổn định Pace, Splits, Pacing]
        
        **2. ❤️ Nhịp tim & Cường độ**
        [Phân tích HR Zones, Cardiac Drift, Power (nếu có)]
        
        **3. ⛅ Tác động Ngoại cảnh**
        [Thời tiết, nhiệt độ ảnh hưởng ra sao]
        
        **💡 TỔNG KẾT & LỜI KHUYÊN**
        [Kết luận hiệu quả bài tập + Lời khuyên cụ thể]
        
        LƯU Ý: Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách.
        """

    # Append AI context to prompt
    if context_str:
        prompt += context_str

    try:
        if Config.ROUTER9_API_KEY:
            ai_report = call_ai_api(Config.ROUTER9_API_KEY, model_to_use, prompt)
            if ai_report and email:
                report_with_time = f"--- [Thời gian báo cáo: {current_now}] ---\n{ai_report}"
                redis_service.save_ai_context(email, mode, report_with_time)
            return ai_report
        else:
             print(f"[{user_label}] ROUTER9_API_KEY not found.")
             return None
    except Exception as e:
        print(f"[{user_label}] AI Error: {str(e)}")
        return None

def get_speech_script(original_text, user_config, prompt_template=None, mode="daily"):
    """
    Dùng Gemini để viết lại nội dung báo cáo thành kịch bản nói tự nhiên.
    """
    user_label = user_config.get('name', 'Bạn')
    print(f"[{user_label}] Writing Voice script...")
    
    context_str = "báo cáo thể thao" if mode == "daily" else "phân tích năng lượng cơ thể" if mode == "battery" else "phân tích giấc ngủ sáng nay"
    
    formatted_prompt = None
    default_model = Config.MODEL_WORKER
    model_to_use = default_model

    if prompt_template and isinstance(prompt_template, dict):
        try:
             # Voice script might not need intricate splitting but consistency helps
             sys_p = prompt_template.get("system_prompt", "")
             user_tmplt = prompt_template.get("user_template", "")
             model_to_use = prompt_template.get("model", default_model)
             
             formatted_user = user_tmplt.format(
                user_label=user_label,
                context_str=context_str,
                original_text=original_text
             )
             formatted_prompt = f"{sys_p}\n\n{formatted_user}"
        except Exception as e:
            print(f"[{user_label}] Error formatting Notion voice prompt (dict): {e}")
            formatted_prompt = None

    elif prompt_template and isinstance(prompt_template, str):
        try:
            formatted_prompt = prompt_template.format(
                user_label=user_label,
                context_str=context_str,
                original_text=original_text
            )
        except Exception as e:
            print(f"[{user_label}] Error formatting Notion voice prompt: {e}")
            formatted_prompt = None

    if formatted_prompt:
        prompt = formatted_prompt
    else:
        prompt = f"""
        Bạn là người bạn thân và cũng là trợ lý trong công việc của {user_label}.
        Dưới đây là một {context_str} của họ:
        ---
        {original_text}
        ---
        Nhiệm vụ: Viết lại thành **KỊCH BẢN ĐỌC (Voice Script)** ngắn gọn, tự nhiên, bỏ emoji, bỏ markdown. Giọng điệu: Hào hứng, năng động, ấm áp, như một người bạn đồng hành.
        """

    try:
        if Config.ROUTER9_API_KEY:
            return call_ai_api(Config.ROUTER9_API_KEY, model_to_use, prompt).strip()
        else:
             print(f"[{user_label}] ROUTER9_API_KEY not found.")
             return "Xin chào, đây là báo cáo sức khỏe của bạn. Hãy kiểm tra tin nhắn văn bản để biết chi tiết."
    except Exception as e:
        print(f"[{user_label}] AI Error: {str(e)}")
        return "Xin chào, đây là báo cáo sức khỏe của bạn. Hãy kiểm tra tin nhắn văn bản để biết chi tiết."

def parse_audio_mime_type(mime_type: str) -> Dict[str, Optional[int]]:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass 
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels, 
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

async def generate_audio_from_text(text, output_file, voice="Sadachbia"):
    """
    Tạo file WAV dùng Gemini TTS.
    """
    print(f"Generating voice with Gemini ({voice})...")
        
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice
                )
            )
        ),
    )
    
    model_name = "gemini-2.5-flash-preview-tts"

    # --- ROTATION LOGIC for TTS (Refactored) ---
    def worker(api_key):
        client = genai.Client(api_key=api_key)
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ),
        ]
        
        all_raw_bytes = bytearray()
        mime_type = None

        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=generate_content_config,
        ):
            if (chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None):
                continue
            
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                if not mime_type:
                    mime_type = part.inline_data.mime_type
                all_raw_bytes.extend(part.inline_data.data)

        if len(all_raw_bytes) > 0:
            final_mime_type = mime_type if mime_type else "audio/L16;rate=24000"
            wav_data = convert_to_wav(all_raw_bytes, final_mime_type)

            final_output_file = output_file
            if not final_output_file.lower().endswith(".wav"):
                    final_output_file = final_output_file.rsplit('.', 1)[0] + ".wav"
            
            # Write file
            with open(final_output_file, "wb") as f:
                f.write(wav_data)
            print(f"Audio saved to {final_output_file}")
            return True
        else:
             raise Exception("Stream finished but no audio data collected.")

    return gemini_key_manager.execute_with_retry(
        worker_func=worker,
        default_return=False,
        verbose_label="Gemini TTS"
    )

def filter_time_series(values_list, start_time=None, end_time=None, downsample_factor=5):
    """
    Lọc danh sách time-series [[ts_ms, val], ...] theo khung giờ HH:MM và giảm tải số lượng điểm dữ liệu.
    """
    import pytz
    from datetime import datetime

    if not values_list:
        return []

    start_min = None
    end_min = None
    if start_time:
        try:
            parts = start_time.split(":")
            start_min = int(parts[0]) * 60 + int(parts[1])
        except Exception: pass
    if end_time:
        try:
            parts = end_time.split(":")
            end_min = int(parts[0]) * 60 + int(parts[1])
        except Exception: pass

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    filtered = []

    for item in values_list:
        if not isinstance(item, list) and not isinstance(item, tuple):
            continue
        if len(item) < 2:
            continue
        ts_ms, val = item[0], item[1]
        if val is None or val < 0:
            continue

        dt = datetime.fromtimestamp(ts_ms / 1000, vn_tz)
        time_str = dt.strftime("%H:%M")
        item_min = dt.hour * 60 + dt.minute

        if start_min is not None and item_min < start_min:
            continue
        if end_min is not None and item_min > end_min:
            continue

        filtered.append({"time": time_str, "value": val})

    if not start_time and not end_time and len(filtered) > 100:
        filtered = filtered[::downsample_factor]

    return filtered

GARMIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_health_summary",
            "description": "Lấy dữ liệu sức khỏe tổng quan trong một ngày cụ thể. Dữ liệu trả về bao gồm nhịp tim nghỉ ngơi (resting heart rate - RHR), tổng số bước chân, mức độ căng thẳng trung bình (average stress), và pin cơ thể hiện tại (body battery). Sử dụng công cụ này khi người dùng hỏi các chỉ số cơ bản của ngày.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD (Ví dụ: 2026-06-24)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sleep_analysis",
            "description": "Phân tích chi tiết giấc ngủ đêm qua hoặc trong một ngày cụ thể. Dữ liệu trả về bao gồm phân phối thời gian ngủ sâu (Deep sleep), ngủ nông (Light sleep), ngủ mơ (REM sleep), thời gian thức giấc (Awake), tổng thời gian ngủ thực tế, và đánh giá chất lượng giấc ngủ. Sử dụng khi người dùng hỏi về giấc ngủ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD. Lưu ý: Ngày của giấc ngủ là ngày thức dậy (Ví dụ: ngủ đêm 23/06 thức dậy sáng 24/06 thì truyền ngày 2026-06-24)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stress_trend",
            "description": "Lấy dữ liệu mức căng thẳng (Stress) chi tiết trong ngày. Hỗ trợ lọc theo khoảng thời gian cụ thể (ví dụ: nhịp stress lúc 14:00 - 16:00) bằng tham số start_time và end_time. Sử dụng khi người dùng hỏi về biến động stress, stress buổi sáng/chiều hoặc stress tại một khung giờ cụ thể.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Giờ bắt đầu cần lọc, định dạng HH:MM (Ví dụ: 07:00). Mặc định là None (không lọc)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Giờ kết thúc cần lọc, định dạng HH:MM (Ví dụ: 08:30). Mặc định là None (không lọc)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_body_battery_trend",
            "description": "Lấy dữ liệu Pin cơ thể (Body Battery) biến động trong ngày và thông tin các giấc ngủ ngắn (naps) nếu có. Hỗ trợ lọc theo khoảng thời gian cụ thể bằng tham số start_time và end_time. Sử dụng khi người dùng hỏi về biến động sạc/xả pin cơ thể, pin cơ thể buổi sáng/tối hoặc ngủ trưa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Giờ bắt đầu cần lọc, định dạng HH:MM (Ví dụ: 07:00)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Giờ kết thúc cần lọc, định dạng HH:MM (Ví dụ: 12:00)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_activities",
            "description": "Lấy danh sách các hoạt động thể thao (chạy bộ, đạp xe, bơi lội, gym...) trong khoảng thời gian xác định. Trả về ID hoạt động, tên, loại hoạt động, thời gian bắt đầu, quãng đường (km), thời gian tập (phút), nhịp tim trung bình, nhịp tim tối đa, calo tiêu hao. Sử dụng khi người dùng hỏi hôm nay/tuần này tập gì, chạy bao nhiêu km.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Ngày bắt đầu tìm kiếm, định dạng YYYY-MM-DD."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Ngày kết thúc tìm kiếm, định dạng YYYY-MM-DD. Nếu để trống sẽ mặc định bằng start_date."
                    }
                },
                "required": ["start_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_activity_details",
            "description": "Lấy chi tiết một bài tập cụ thể bằng ID bài tập (activity_id). Dữ liệu trả về bao gồm splits (tốc độ/pace theo từng km), thời tiết khi tập, nhịp tim theo vùng (HR zones), và biểu đồ thời gian thực. Sử dụng khi người dùng hỏi sâu về phân tích kỹ thuật của một hoạt động thể thao cụ thể.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "integer",
                        "description": "ID bài tập (activityId) lấy từ danh sách hoạt động."
                    }
                },
                "required": ["activity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hrv_data",
            "description": "Lấy dữ liệu biến thiên nhịp tim HRV (Heart Rate Variability) đêm qua hoặc ngày cụ thể. Dữ liệu bao gồm trạng thái HRV (HRV Status: Balanced, Unbalanced...), trị số HRV trung bình đêm qua (lastNightAvg), trung bình tuần (weeklyAvg), và khoảng tham chiếu (baseline). Sử dụng khi người dùng hỏi về HRV hoặc mức độ phục hồi hệ thần kinh tự chủ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spo2_data",
            "description": "Lấy dữ liệu nồng độ oxy trong máu SpO2 trung bình, thấp nhất và đo gần nhất trong ngày. Sử dụng khi người dùng hỏi về SpO2 hoặc nồng độ oxy khi ngủ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_respiration_data",
            "description": "Lấy dữ liệu nhịp thở (Respiration/Breathing Rate) trung bình khi thức, khi ngủ, thấp nhất và cao nhất trong ngày. Đơn vị đo là breaths per minute (brpm). Sử dụng khi người dùng hỏi về nhịp thở.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_training_readiness",
            "description": "Lấy điểm sẵn sàng tập luyện (Training Readiness) từ 1-100 và đánh giá (Poor, Good, Prime...). Trả về chi tiết các yếu tố cấu thành: thời gian phục hồi còn lại (recoveryTimeHours), chất lượng giấc ngủ (sleepHistoryScore), trạng thái HRV, lịch sử stress, và lịch sử tập luyện. Sử dụng khi người dùng hỏi 'Hôm nay mình có nên tập nặng không?' hoặc hỏi về độ sẵn sàng tập luyện.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_training_status",
            "description": "Lấy trạng thái tập luyện hiện tại (Training Status) ví dụ: Productive (Hiệu quả), Peaking (Đạt đỉnh), Maintaining (Duy trì), Detraining (Ngừng tập). Cung cấp thông tin về chỉ số VO2 Max, trạng thái thể lực (fitnessStatus), tải tập luyện hiện tại (loadStatus), và tải tập luyện 7 ngày qua (sevenDayAcuteLoad). Sử dụng khi người dùng hỏi về VO2 Max, tải tập luyện hoặc trạng thái huấn luyện dài hạn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_heart_rates",
            "description": "Lấy dữ liệu nhịp tim chi tiết (time-series) theo từng mốc thời gian trong ngày. Hỗ trợ lọc theo giờ cụ thể bằng start_time và end_time. Sử dụng khi người dùng hỏi các câu hỏi cụ thể như: 'Nhịp tim của mình lúc 7h sáng đến 8h sáng là bao nhiêu?' hoặc 'Nhịp tim lúc chạy bộ chiều nay biến động thế nào?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Giờ bắt đầu cần lọc, định dạng HH:MM (Ví dụ: 07:00)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Giờ kết thúc cần lọc, định dạng HH:MM (Ví dụ: 08:00)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_steps_trend",
            "description": "Lấy dữ liệu bước chân chi tiết (time-series) theo từng khoảng thời gian trong ngày. Hỗ trợ lọc theo giờ cụ thể bằng start_time và end_time. Sử dụng khi người dùng hỏi chi tiết như: 'Khung giờ nào mình đi bộ nhiều nhất?' hoặc 'Từ 8h đến 10h sáng mình đi được bao nhiêu bước?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Giờ bắt đầu lọc, định dạng HH:MM (Ví dụ: 08:00)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Giờ kết thúc lọc, định dạng HH:MM (Ví dụ: 10:00)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hydration_data",
            "description": "Lấy dữ liệu theo dõi lượng nước uống (Hydration) trong ngày, lượng nước mục tiêu (ml) và lượng mồ hôi thất thoát ước tính khi tập luyện. Sử dụng khi người dùng hỏi hôm nay đã uống bao nhiêu nước, cần uống thêm bao nhiêu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_max_metrics",
            "description": "Lấy các chỉ số thể chất tối đa (Max metrics) bao gồm lịch sử VO2 Max chi tiết cho các môn thể thao (chạy bộ, đạp xe) và độ tuổi thể chất (Fitness Age). Sử dụng khi người dùng hỏi chi tiết về độ tuổi thể chất hoặc tiến trình VO2 Max.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lactate_threshold",
            "description": "Lấy ngưỡng Lactate (Lactate Threshold) bao gồm nhịp tim ngưỡng (threshold HR - bpm) và tốc độ ngưỡng (threshold pace/speed - m/s) được đồng hồ Garmin ghi nhận tự động. Sử dụng khi người dùng hỏi về ngưỡng acid lactic hoặc các chỉ số nâng cao để lập giáo án chạy bộ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_personal_records",
            "description": "Lấy danh sách kỷ lục cá nhân (Personal Records - PR) của người dùng ở các cự ly chạy bộ (1km, 5km, 10k, Half Marathon, Marathon, hoạt động xa nhất), bơi lội, đạp xe. Sử dụng khi người dùng hỏi 'Kỷ lục 5k của mình là bao nhiêu?' hoặc các câu hỏi tương tự.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_race_predictions",
            "description": "Lấy dự báo thành tích thi đấu (Race Predictions) cho các cự ly chạy bộ phổ biến: 5km, 10km, Half Marathon (21km), và Marathon (42km) dựa trên dữ liệu VO2 Max và lịch sử tập luyện. Sử dụng khi người dùng hỏi dự báo thời gian hoàn thành cuộc đua hoặc khả năng chạy hiện tại.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Ngày bắt đầu lấy dự báo định dạng YYYY-MM-DD. Nếu trống sẽ mặc định là hôm nay."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Ngày kết thúc định dạng YYYY-MM-DD."
                    }
                },
                "required": ["start_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fitness_age",
            "description": "Lấy thông tin chi tiết về độ tuổi thể chất (Fitness Age) của người dùng cùng với các khuyến nghị để cải thiện độ tuổi thể chất (ví dụ: giảm BMI, tăng thời gian vận động cường độ cao). Sử dụng khi người dùng hỏi về tuổi thể chất.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_endurance_score",
            "description": "Lấy điểm bền bỉ (Endurance Score) của Garmin đo khả năng duy trì vận động kéo dài của cơ thể và các yếu tố đóng góp từ các hoạt động trước đó. Sử dụng khi người dùng hỏi về điểm bền bỉ hoặc khả năng sức bền.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Ngày bắt đầu, định dạng YYYY-MM-DD."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Ngày kết thúc, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["start_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hill_score",
            "description": "Lấy điểm leo dốc (Hill Score) của Garmin đo khả năng chạy lên dốc dựa trên sức mạnh leo dốc (hill strength) và sức bền leo dốc (hill endurance). Sử dụng khi người dùng hỏi về điểm leo dốc hoặc khả năng chạy địa hình/dốc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Ngày bắt đầu, định dạng YYYY-MM-DD."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Ngày kết thúc, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["start_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_intensity_minutes",
            "description": "Lấy số phút vận động cường độ cao (Intensity Minutes) trong ngày bao gồm số phút cường độ trung bình (moderate), cường độ mạnh (vigorous) và tổng số phút tích lũy so với mục tiêu tuần. Sử dụng khi người dùng hỏi về thời gian vận động tích lũy trong ngày.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy dữ liệu, định dạng YYYY-MM-DD."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_devices",
            "description": "Lấy danh sách các thiết bị đồng hồ Garmin (Devices) của người dùng hiện đang kết nối với tài khoản, bao gồm tên thiết bị, mã model, số serial, phiên bản phần mềm. Sử dụng khi người dùng hỏi về thông tin đồng hồ đang sử dụng.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

def execute_garmin_tool(client, name: str, args: dict, user_label: str = "User") -> str:
    """
    Thực thi các hàm lấy dữ liệu Garmin tương ứng với Tool Call của AI.
    """
    import json
    if not client:
        return json.dumps({"error": "Garmin client is not logged in. Tell user to login or configure credentials."})

    date_str = args.get("date")

    try:
        if name == "get_health_summary":
            summary = client.get_user_summary(date_str)
            stats = summary.get('stats', summary)
            rhr = stats.get('restingHeartRate') or 0
            stress = stats.get('averageStressLevel') or 0
            bb_val = summary.get('stats_and_body', {}).get('bodyBatteryMostRecentValue')
            if bb_val is None: bb_val = stats.get('bodyBatteryMostRecentValue') or 0
            steps = stats.get('steps') or stats.get('totalSteps') or 0
            return json.dumps({
                "resting_heart_rate": rhr,
                "average_stress": stress,
                "body_battery": bb_val,
                "steps": steps
            }, ensure_ascii=False)

        elif name == "get_sleep_analysis":
            from app.services.garmin_service import get_sleep_analysis
            _, sleep_desc = get_sleep_analysis(client, date_str, user_label)
            return json.dumps({"sleep_analysis": sleep_desc}, ensure_ascii=False)

        elif name == "get_stress_trend":
            stress_data = client.get_all_day_stress(date_str) or {}
            stress_values = stress_data.get("stressValuesArray") or []
            filtered_stress = filter_time_series(stress_values, args.get("start_time"), args.get("end_time"), downsample_factor=5)

            avg_stress = stress_data.get('avgStress') or stress_data.get('averageStressLevel')
            stress_duration = stress_data.get('stressDuration')
            return json.dumps({
                "average_stress": avg_stress,
                "stress_duration_details": stress_duration,
                "stress_readings_count": len(filtered_stress),
                "stress_readings": filtered_stress
            }, ensure_ascii=False)

        elif name == "get_body_battery_trend":
            # get_all_day_stress contains bodyBatteryValuesArray
            stress_data = client.get_all_day_stress(date_str) or {}
            bb_values = stress_data.get("bodyBatteryValuesArray") or []
            filtered_bb = filter_time_series(bb_values, args.get("start_time"), args.get("end_time"), downsample_factor=5)

            events = client.get_body_battery_events(date_str) or []
            naps = [e for e in events if e.get('eventType') == 'NAP']

            nap_details = []
            for nap in naps:
                dur_ms = nap.get('durationInMilliseconds') or 0
                nap_details.append({
                    "start_time": nap.get('startTimeLocal'),
                    "duration_minutes": int(dur_ms / 60000)
                })

            charged = stress_data.get('chargedValue') or 0
            drained = stress_data.get('drainedValue') or 0

            return json.dumps({
                "charged": charged,
                "drained": drained,
                "naps": nap_details,
                "body_battery_readings_count": len(filtered_bb),
                "body_battery_readings": filtered_bb
            }, ensure_ascii=False)

        elif name == "get_activities":
            start = args.get("start_date")
            end = args.get("end_date") or start
            activities = client.get_activities_by_date(start, end) or []

            results = []
            for act in activities:
                results.append({
                    "activityId": act.get("activityId"),
                    "activityName": act.get("activityName"),
                    "activityType": act.get("activityType", {}).get("typeKey"),
                    "startTimeLocal": act.get("startTimeLocal"),
                    "duration_minutes": round(act.get("duration", 0) / 60, 1),
                    "distance_km": round(act.get("distance", 0) / 1000, 2),
                    "averageHR": act.get("averageHR"),
                    "maxHR": act.get("maxHR"),
                    "calories": act.get("calories")
                })
            return json.dumps(results, ensure_ascii=False)

        elif name == "get_activity_details":
            act_id = args.get("activity_id")
            splits = None
            try:
                splits = client.get_activity_splits(act_id)
            except Exception: pass

            weather = None
            try:
                weather = client.get_activity_weather(act_id)
            except Exception: pass

            hr_zones = None
            try:
                hr_zones = client.get_activity_hr_in_timezones(act_id)
            except Exception: pass

            return json.dumps({
                "activityId": act_id,
                "splits": splits,
                "weather": weather,
                "hr_zones": hr_zones
            }, ensure_ascii=False)

        elif name == "get_hrv_data":
            hrv = client.get_hrv_data(date_str) or {}
            hrv_summary = hrv.get("hrvSummary") or hrv
            return json.dumps({
                "hrvStatus": hrv_summary.get("hrvStatus"),
                "lastNightAvg": hrv_summary.get("lastNightAvg"),
                "weeklyAvg": hrv_summary.get("weeklyAvg"),
                "baseline": hrv_summary.get("baseline")
            }, ensure_ascii=False)

        elif name == "get_spo2_data":
            spo2 = client.get_spo2_data(date_str) or {}
            return json.dumps({
                "averageSpO2": spo2.get("averageSpO2"),
                "lowestSpO2": spo2.get("lowestSpO2"),
                "latestSpO2": spo2.get("latestSpO2")
            }, ensure_ascii=False)

        elif name == "get_respiration_data":
            resp = client.get_respiration_data(date_str) or {}
            return json.dumps({
                "avgWakingRespirationValue": resp.get("avgWakingRespirationValue"),
                "avgSleepRespirationValue": resp.get("avgSleepRespirationValue"),
                "lowestRespirationValue": resp.get("lowestRespirationValue"),
                "highestRespirationValue": resp.get("highestRespirationValue")
            }, ensure_ascii=False)

        elif name == "get_training_readiness":
            readiness = client.get_training_readiness(date_str) or {}
            r_map = readiness.get("trainingReadinessMap") or readiness
            return json.dumps({
                "score": r_map.get("scoreValue"),
                "assessment": r_map.get("readinessAssessment"),
                "recovery_time_hours": r_map.get("recoveryTimeHours"),
                "sleep_history_score": r_map.get("sleepHistoryScoreValue"),
                "hrv_status": r_map.get("hrvStatus"),
                "stress_history_score": r_map.get("stressHistoryScoreValue")
            }, ensure_ascii=False)

        elif name == "get_training_status":
            status = client.get_training_status(date_str) or {}
            ts_map = status.get("trainingStatusAssessment") or status
            return json.dumps({
                "trainingStatus": ts_map.get("trainingStatus"),
                "vo2Max": status.get("vo2Max"),
                "fitnessStatus": ts_map.get("fitnessStatus"),
                "loadStatus": ts_map.get("loadStatus"),
                "sevenDayAcuteLoad": status.get("sevenDayAcuteLoad")
            }, ensure_ascii=False)

        elif name == "get_heart_rates":
            hr_data = client.get_heart_rates(date_str) or {}
            hr_values = hr_data.get("heartRateValues") or []
            filtered_hr = filter_time_series(hr_values, args.get("start_time"), args.get("end_time"), downsample_factor=5)
            return json.dumps({
                "restingHeartRate": hr_data.get("restingHeartRate"),
                "maxHeartRate": hr_data.get("maxHeartRate"),
                "minHeartRate": hr_data.get("minHeartRate"),
                "heart_rate_readings_count": len(filtered_hr),
                "heart_rate_readings": filtered_hr
            }, ensure_ascii=False)

        elif name == "get_steps_trend":
            steps_data = client.get_steps_data(date_str) or []
            results = []

            start_t = args.get("start_time")
            end_t = args.get("end_time")

            start_min = None
            end_min = None
            if start_t:
                try:
                    parts = start_t.split(":")
                    start_min = int(parts[0]) * 60 + int(parts[1])
                except Exception: pass
            if end_t:
                try:
                    parts = end_t.split(":")
                    end_min = int(parts[0]) * 60 + int(parts[1])
                except Exception: pass

            import pytz
            from datetime import datetime
            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

            for entry in steps_data:
                steps_count = entry.get("steps") or 0
                if steps_count <= 0:
                    continue

                time_to_use = entry.get("startGMT") or entry.get("startTimeGMT") or entry.get("startTimeLocal")
                if not time_to_use:
                    continue

                try:
                    t_str = time_to_use.replace("T", " ")
                    if "." in t_str:
                        t_str = t_str.split(".")[0]

                    if "GMT" in time_to_use or "startGMT" in entry or "startTimeGMT" in entry:
                        dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
                        dt_local = dt_utc.astimezone(vn_tz)
                    else:
                        dt_local = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=vn_tz)

                    item_min = dt_local.hour * 60 + dt_local.minute
                    time_label = dt_local.strftime("%H:%M")

                    if start_min is not None and item_min < start_min:
                        continue
                    if end_min is not None and item_min > end_min:
                        continue

                    results.append({
                        "time": time_label,
                        "steps": steps_count,
                        "activity_level": entry.get("primaryActivityLevel")
                    })
                except Exception:
                    pass

            return json.dumps(results, ensure_ascii=False)

        elif name == "get_hydration_data":
            hydration = client.get_hydration_data(date_str)
            return json.dumps(hydration, ensure_ascii=False)

        elif name == "get_max_metrics":
            max_metrics = client.get_max_metrics(date_str)
            return json.dumps(max_metrics, ensure_ascii=False)

        elif name == "get_lactate_threshold":
            lactate = client.get_lactate_threshold(date_str)
            return json.dumps(lactate, ensure_ascii=False)

        elif name == "get_personal_records":
            records = client.get_personal_record()
            return json.dumps(records, ensure_ascii=False)

        elif name == "get_race_predictions":
            predictions = client.get_race_predictions(
                startdate=args.get("start_date"),
                enddate=args.get("end_date")
            )
            return json.dumps(predictions, ensure_ascii=False)

        elif name == "get_fitness_age":
            fitness_age = client.get_fitnessage_data(date_str)
            return json.dumps(fitness_age, ensure_ascii=False)

        elif name == "get_endurance_score":
            endurance = client.get_endurance_score(
                startdate=args.get("start_date"),
                enddate=args.get("end_date")
            )
            return json.dumps(endurance, ensure_ascii=False)

        elif name == "get_hill_score":
            hill = client.get_hill_score(
                startdate=args.get("start_date"),
                enddate=args.get("end_date")
            )
            return json.dumps(hill, ensure_ascii=False)

        elif name == "get_intensity_minutes":
            intensity = client.get_intensity_minutes_data(date_str)
            return json.dumps(intensity, ensure_ascii=False)

        elif name == "get_devices":
            devices = client.get_devices()
            return json.dumps(devices, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        print(f"[{user_label}] Error executing tool {name}: {e}")
        return json.dumps({"error": f"Lỗi khi truy xuất dữ liệu {name}: {str(e)}"}, ensure_ascii=False)

def call_ai_api_raw(api_key, model_name, messages, tools=None):
    from openai import OpenAI
    client = OpenAI(
        base_url="https://khoitran1999-claude-server.hf.space/v1",
        api_key=api_key
    )
    kwargs = {
        "model": model_name,
        "messages": messages,
        "stream": False
    }
    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message

async def call_ai_api_raw_async(api_key, model_name, messages, tools=None):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        base_url="https://khoitran1999-claude-server.hf.space/v1",
        api_key=api_key
    )
    kwargs = {
        "model": model_name,
        "messages": messages,
        "stream": False
    }
    if tools:
        kwargs["tools"] = tools

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message

async def process_data_with_worker(tool_name: str, tool_args: dict, raw_data_str: str, user_label: str = "User") -> str:
    """
    Sử dụng MODEL_WORKER để xử lý và tóm tắt dữ liệu Garmin Connect thô trước khi trả về cho MODEL_BRAIN.
    """
    import json
    try:
        data = json.loads(raw_data_str)
        if isinstance(data, dict) and "error" in data:
            return raw_data_str
    except Exception:
        pass

    if not Config.ROUTER9_API_KEY:
        return raw_data_str

    prompt = f"""
    Bạn là Trợ lý phân tích dữ liệu Garmin chuyên sâu (MODEL_WORKER).
    Nhiệm vụ của bạn là đọc dữ liệu thô từ API Garmin Connect, lọc sạch, phân tích ngắn gọn và định dạng lại thành cấu trúc dễ đọc nhất để gửi cho MODEL_BRAIN.

    Mục tiêu công cụ: {tool_name}
    Các tham số yêu cầu: {json.dumps(tool_args, ensure_ascii=False)}

    YÊU CẦU PHÂN TÍCH:
    1. Trích xuất các số liệu quan trọng nhất (ví dụ: trị số trung bình, thời điểm cao nhất/thấp nhất, bất thường).
    2. Lọc bỏ các thông tin rác, rỗng hoặc các trường kỹ thuật không cần thiết để tối ưu hóa tokens.
    3. Định dạng kết quả dạng văn bản ngắn gọn, có gạch đầu dòng rõ ràng.
    4. Giữ nguyên tính chính xác tuyệt đối của các con số. Không tự bịa thông tin.
    5. Nếu dữ liệu rỗng hoặc không có gì, hãy nói rõ không ghi nhận được chỉ số nào.

    DỮ LIỆU THÔ (JSON) TỪ GARMIN:
    ---
    {raw_data_str}
    ---

    Hãy trả về báo cáo phân tích cô đọng của bạn (dưới 250 từ):
    """

    try:
        print(f"[{user_label}] 🤖 Sending raw data of {tool_name} to MODEL_WORKER for preprocessing...")
        messages = [
            {"role": "system", "content": "You are a professional Garmin health data analyst. Answer in Vietnamese."},
            {"role": "user", "content": prompt}
        ]
        response_msg = await call_ai_api_raw_async(
            api_key=Config.ROUTER9_API_KEY,
            model_name=Config.MODEL_WORKER,
            messages=messages
        )
        worker_summary = response_msg.content or raw_data_str
        print(f"[{user_label}] 🧠 MODEL_WORKER finished processing {tool_name}.")
        return worker_summary
    except Exception as e:
        print(f"[{user_label}] ⚠️ Error in MODEL_WORKER processing {tool_name}: {e}. Falling back to raw data.")
        return raw_data_str

async def get_customer_service_advice(tele_id: str, question: str, user_config: dict, prompt_template: dict = None, garmin_context: str = None, garmin_client = None) -> str:
    """
    Hỏi đáp hỗ trợ về tính năng và dữ liệu của Garmin Connect sử dụng Tool Calling / Agent.
    """
    user_label = user_config.get('name', 'VĐV')
    email = user_config.get('email')

    # 1. Đọc lịch sử chat từ Redis
    history = redis_service.get_chat_history(tele_id, limit=10)
    history_str = ""
    if history:
        for msg in history:
            role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            history_str += f"{role_label}: {msg['content']}\n"
    else:
        history_str = "(Không có lịch sử trò chuyện gần đây)\n"

    # 2. Đọc tài liệu hỗ trợ HELP.md
    help_doc = ""
    help_path = os.path.join(os.getcwd(), "HELP.md")
    if os.path.exists(help_path):
        try:
            with open(help_path, "r", encoding="utf-8") as f:
                help_doc = f.read()
        except Exception as e:
            print(f"Error reading HELP.md: {e}")
            help_doc = "Tài liệu trợ giúp không khả dụng tại local."
    else:
        help_doc = "Tài liệu trợ giúp không tồn tại."

    # 3. Chuẩn bị prompt
    default_model = Config.MODEL_BRAIN
    model_to_use = default_model

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    current_date_str = datetime.now(vn_tz).strftime("%Y-%m-%d")

    goal = user_config.get('goal', 'Duy trì sức khỏe')
    injury = user_config.get('injury', 'Không có')
    note = user_config.get('note', '')
    user_profile = f"Mục tiêu: {goal} | Chấn thương: {injury} | Ghi chú thêm: {note}"

    system_instruction = f"""Bạn là Trợ lý hỗ trợ khách hàng thân thiện của Garmin AI Coach Pro.
Nhiệm vụ của bạn là giải đáp thắc mắc của người dùng về các tính năng, cách thức hoạt động, nguồn dữ liệu và các vấn đề kỹ thuật dựa trên tài liệu được cung cấp.

Tài khoản Garmin Connect của người dùng hiện ĐÃ ĐĂNG NHẬP thành công và sẵn sàng để truy xuất dữ liệu.
Nếu câu hỏi của người dùng liên quan đến dữ liệu cá nhân, sức khỏe, giấc ngủ, tập luyện hoặc bất kỳ chỉ số nào từ Garmin của họ, bạn PHẢI sử dụng các công cụ (tools) được cung cấp để lấy dữ liệu tương ứng.
Hãy luôn mặc định ngày cần lấy là hôm nay ({current_date_str}) trừ khi người dùng nói cụ thể mốc thời gian khác (ví dụ: hôm qua, 3 ngày trước, ngày 2026-06-20). Hãy quy đổi thông minh các mốc thời gian này về định dạng YYYY-MM-DD dựa trên ngày hôm nay.

Sau khi gọi tools và lấy được dữ liệu, hãy phân tích kỹ, tổng hợp và đưa ra đánh giá, nhận xét cũng như lời khuyên cá nhân hóa hữu ích dựa trên hồ sơ của người dùng.

Hồ sơ người dùng:
- {user_profile}

Ngày hiện tại (Hôm nay): {current_date_str}

TÀI LIỆU HƯỚNG DẪN & THÔNG TIN HỆ THỐNG:
---
{help_doc}
---

YÊU CẦU:
1. Trả lời trực tiếp, rõ ràng câu hỏi của người dùng.
2. Dựa hoàn toàn vào tài liệu và dữ liệu sức khỏe từ các công cụ (nếu có) để trả lời. Không tự chế thông tin không có trong tài liệu/dữ liệu trả về.
3. Nếu câu hỏi liên quan đến chỉ số sức khỏe của người dùng mà bạn không thể truy xuất được hoặc công cụ báo lỗi, hãy lịch sự thông báo cho họ đồng bộ thiết bị hoặc thử lại sau.
4. Giọng điệu thân thiện, chu đáo, hỗ trợ nhiệt tình.
5. Trả về định dạng Markdown Telegram (sử dụng dấu * để bold, dùng dấu • cho danh sách).
"""

    if prompt_template and isinstance(prompt_template, dict):
        sys_p = prompt_template.get("system_prompt", "")
        if sys_p:
            system_instruction = f"{sys_p}\n\nThông tin hệ thống & Người dùng:\n- Ngày hôm nay: {current_date_str}\n- Hồ sơ người dùng: {user_profile}\n- Tài liệu trợ giúp:\n{help_doc}"

    # Build conversation messages
    messages = [{"role": "system", "content": system_instruction}]

    # Add historical messages (convert roles if needed, ensuring they follow OpenAI standard)
    if history:
        for msg in history:
            role = msg.get("role")
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": msg.get("content", "")})

    # Add current query
    user_query = question
    if prompt_template and isinstance(prompt_template, dict):
        user_tmplt = prompt_template.get("user_template", "")
        model_to_use = prompt_template.get("model", default_model)
        if user_tmplt:
            try:
                user_query = user_tmplt.format(
                    user_label=user_label,
                    help_doc=help_doc,
                    chat_history=history_str,
                    question=question,
                    garmin_info=garmin_context or "",
                    garmin_context=garmin_context or ""
                )
            except Exception:
                pass

    messages.append({"role": "user", "content": user_query})

    # 4. Gọi AI với Tool Calling loop
    try:
        if Config.ROUTER9_API_KEY:
            max_iterations = 5
            for iteration in range(max_iterations):
                print(f"[{user_label}] Calling LLM (iteration {iteration+1})...")
                response_msg = await call_ai_api_raw_async(
                    api_key=Config.ROUTER9_API_KEY,
                    model_name=model_to_use,
                    messages=messages,
                    tools=GARMIN_TOOLS if garmin_client else None
                )

                # Check for tool calls
                if response_msg.tool_calls:
                    # Append assistant message with tool calls
                    assistant_msg = {
                        "role": "assistant",
                        "content": response_msg.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in response_msg.tool_calls
                        ]
                    }
                    messages.append(assistant_msg)

                    # Helper to execute a single tool pipeline async
                    async def run_single_tool_pipeline(tc):
                        tool_name = tc.function.name
                        import json
                        try:
                            tool_args = json.loads(tc.function.arguments)
                        except Exception as je:
                            print(f"Error parsing tool args: {je}")
                            tool_args = {}

                        # Normalize/fallback dates
                        if "date" in tool_args and not tool_args["date"]:
                            tool_args["date"] = current_date_str
                        if "start_date" in tool_args and not tool_args["start_date"]:
                            tool_args["start_date"] = current_date_str

                        print(f"[{user_label}] 🛠️ AI requests tool: {tool_name} with args {tool_args}")

                        # 1. Fetch Garmin Connect raw data in a non-blocking thread
                        import asyncio
                        raw_result = await asyncio.to_thread(execute_garmin_tool, garmin_client, tool_name, tool_args, user_label)

                        # 2. Process raw data with MODEL_WORKER LLM
                        processed_result = await process_data_with_worker(tool_name, tool_args, raw_result, user_label)

                        return {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tool_name,
                            "content": processed_result
                        }

                    # Execute all requested tools in parallel
                    import asyncio
                    tool_tasks = [run_single_tool_pipeline(tc) for tc in response_msg.tool_calls]
                    tool_responses = await asyncio.gather(*tool_tasks)

                    # Append tool responses to messages history
                    messages.extend(tool_responses)

                    # Continue loop to send tool responses back to LLM
                    continue
                else:
                    # Final answer received
                    ai_reply = response_msg.content
                    if ai_reply:
                        redis_service.save_chat_message(tele_id, "user", question, limit=10)
                        redis_service.save_chat_message(tele_id, "assistant", ai_reply, limit=10)
                    return ai_reply

            return "Không thể hoàn thành yêu cầu vì vượt quá số lần gọi công cụ cho phép."
        else:
            print(f"[{user_label}] ROUTER9_API_KEY not found.")
            return "Tính năng hỏi đáp chưa được cấu hình ROUTER9_API_KEY."
    except Exception as e:
        print(f"[{user_label}] AI CS Error in agent loop: {str(e)}")
        import traceback
        traceback.print_exc()
        return "Hiện tại trợ lý AI đang bận. Vui lòng thử lại sau."


def route_ask_query(question: str, current_date_str: str) -> dict:
    """
    Sử dụng AI để phân tích câu hỏi người dùng và quyết định xem có cần lấy dữ liệu Garmin không.
    """
    prompt = f"""
    Bạn là Router phân loại câu hỏi cho Garmin AI Coach.
    Hãy phân tích câu hỏi của người dùng và ngày hiện tại để quyết định xem hệ thống có cần truy xuất dữ liệu sức khỏe/tập luyện từ Garmin Connect hay không.

    Ngày hiện tại (Hôm nay): {current_date_str}

    Các loại dữ liệu có thể lấy:
    - "summary": Chỉ số tổng quan (Nhịp tim nghỉ RHR, stress trung bình, body battery hiện tại, SpO2, nhịp thở, hrv, trạng thái tập luyện).
    - "sleep": Chi tiết giấc ngủ đêm qua hoặc các đêm trước (thời gian ngủ sâu, ngủ nông, REM, thời gian thức).
    - "activities": Hoạt động thể thao (chạy bộ, đạp xe, bơi lội, pace, quãng đường, nhịp tim khi tập).
    - "timeseries": Biểu đồ chi tiết 24h qua (stress và pin cơ thể biến động theo từng mốc 2h).

    Trả về kết quả dưới dạng JSON duy nhất, KHÔNG chứa thêm bất kỳ text giải thích nào khác ngoài JSON, định dạng như sau:
    {{
      "needs_garmin_data": true hoặc false,
      "metrics": danh sách các chuỗi (chọn từ ["summary", "sleep", "activities", "timeseries"]),
      "date": "YYYY-MM-DD" (Quy đổi các mốc thời gian như "hôm qua", "hôm nay", "sáng nay", "tối qua", "ngày mai" về định dạng ngày cụ thể YYYY-MM-DD dựa trên ngày hiện tại)
    }}

    Ví dụ 1:
    Câu hỏi: "stress buổi sáng của mình là bao nhiêu"
    Kết quả:
    {{
      "needs_garmin_data": true,
      "metrics": ["summary", "timeseries"],
      "date": "{current_date_str}"
    }}

    Ví dụ 2:
    Câu hỏi: "Làm thế nào để đổi múi giờ trên Garmin?"
    Kết quả:
    {{
      "needs_garmin_data": false,
      "metrics": [],
      "date": "{current_date_str}"
    }}

    Hãy phân tích câu hỏi sau:
    Câu hỏi: "{question}"
    """

    default_res = {
        "needs_garmin_data": False,
        "metrics": [],
        "date": current_date_str
    }

    try:
        if not Config.ROUTER9_API_KEY:
            return default_res

        model_to_use = Config.MODEL_BRAIN
        response_text = call_ai_api(Config.ROUTER9_API_KEY, model_to_use, prompt)

        import json
        import re

        cleaned_text = response_text.strip()
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            cleaned_text = json_match.group(0)

        data = json.loads(cleaned_text)
        return {
            "needs_garmin_data": bool(data.get("needs_garmin_data", False)),
            "metrics": list(data.get("metrics", [])),
            "date": str(data.get("date", current_date_str))
        }
    except Exception as e:
        print(f"⚠️ Error in route_ask_query: {e}")
        return default_res

