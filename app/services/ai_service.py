import os
import pytz
import time
import struct
import random
from datetime import datetime
from typing import Optional, Dict
from google import genai
from google.genai import types
from app.config import Config

class GeminiKeyManager:
    """
    Quản lý danh sách API Key và xoay vòng (Round Robin) + Failover.
    """
    def __init__(self):
        self.keys = []
        self._load_keys()
        self.current_index = 0

    def _load_keys(self):
        self.keys = Config.GEMINI_API_KEYS
        print(f"🔑 Loaded {len(self.keys)} Gemini Keys from Config.")

    def get_current_key(self):
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate_key(self):
        """Chuyển sang key tiếp theo trong danh sách."""
        if not self.keys:
            return None
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"🔄 Switching to API Key Index: {self.current_index}")
        return self.get_current_key()
    
    def get_key_count(self):
        return len(self.keys)

    def execute_with_retry(self, worker_func, default_return=None, verbose_label="Service"):
        """
        Thực thi worker_func với logic Retry & Rotate Key.
        worker_func(api_key) -> result
        """
        max_attempts = self.get_key_count() * 2
        if max_attempts == 0: 
            print(f"[{verbose_label}] ⚠️ Không có API Key nào để thực thi.")
            return default_return

        for attempt in range(max_attempts):
            current_api_key = self.get_current_key()
            try:
                # Thực thi logic chính
                result = worker_func(current_api_key)
                
                # Thành công -> Rotate để load balancing
                self.rotate_key()
                return result

            except Exception as e:
                error_msg = str(e)
                print(f"[{verbose_label}] ⚠️ Lỗi AI (Key ...{current_api_key[-5:] if current_api_key else 'None'}): {error_msg}")
                
                # Logic xử lý lỗi + Rotate
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                    print(f"   --> Quota Exceeded. Rotating key...")
                    self.rotate_key()
                    time.sleep(1)
                else:
                    self.rotate_key()
                    time.sleep(2)

        print(f"[{verbose_label}] ❌ Đã thử tất cả các keys nhưng vẫn thất bại.")
        return default_return

# Khởi tạo Global Instance
key_manager = GeminiKeyManager()

def get_ai_advice(today, r_data, r_score, l_data, user_config, prompt_template=None, mode="daily"):
    """
    Gọi AI để lấy lời khuyên. Tự động xoay key khi gặp lỗi Quota.
    """
    # Lấy thông tin cá nhân hóa từ Notion
    user_label = user_config.get('name', 'VĐV')
    goal = user_config.get('goal', 'Duy trì sức khỏe')
    injury = user_config.get('injury', 'Không có')
    note = user_config.get('note', '')

    print(f"[{user_label}] 🧠 Đang gọi AI Coach (Mode: {mode} | Context: {goal})...")
    
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

    
    # Pre-calculate derived values for safe formatting
    avg_daily_load_int = int(l_data['avg_daily_load']) if l_data and 'avg_daily_load' in l_data else 0

    formatted_prompt = None
    model_to_use = "gemini-3-flash-preview"

    if prompt_template and isinstance(prompt_template, dict):
        try:
            # New structure: system_prompt, user_template, model
            sys_p = prompt_template.get("system_prompt", "")
            user_tmplt = prompt_template.get("user_template", "")
            model_to_use = prompt_template.get("model", "gemini-3-flash-preview")
            
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
                resp_text=resp_text
            )
            
            # Concatenate System + User. Or better: keep them separate if API supports. 
            # But generate_content usually takes string or list.
            # Let's combine them for simplicity:
            formatted_prompt = f"{sys_p}\n\n{formatted_user_part}"

        except Exception as e:
            print(f"[{user_label}] ⚠️ Error formatting Notion prompt ({mode}): {e}")
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
                resp_text=resp_text
            )
         except Exception as e:
            print(f"[{user_label}] ⚠️ Error formatting Notion string prompt ({mode}): {e}")
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
        - **SpO2 (Oxy máu):** {spo2_text}
        - **Hô hấp (Respiration):** {resp_text}

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
        - **SpO2:** {spo2_text}
        - **Hô hấp:** {resp_text}

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

    # --- CƠ CHẾ XOAY VÒNG KEY & RETRY (Refactored) ---
    def worker(api_key):
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_to_use, 
            contents=prompt
        )
        return response.text

    return key_manager.execute_with_retry(
        worker_func=worker,
        default_return="AI Coach đang bận hoặc hết Quota tất cả các key. Vui lòng thử lại sau.",
        verbose_label=user_label
    )

def get_workout_analysis_advice(activity_data_list, user_config, prompt_template=None):
    """
    Phân tích chi tiết (Time-series) các bài tập trong 24h.
    """
    user_label = user_config.get('name', 'VĐV')
    goal = user_config.get('goal', 'Cải thiện thành tích')
    
    print(f"[{user_label}] 🧠 Đang phân tích chi tiết bài tập...")
    
    if not activity_data_list:
        return None

    # Serialization
    import json
    activities_json = json.dumps(activity_data_list, ensure_ascii=False, default=str)
    
    vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    current_now = datetime.now(vn_timezone).strftime("%H:%M:%S, %d/%m/%Y")

    formatted_prompt = None
    model_to_use = "gemini-3-flash-preview"

    if prompt_template and isinstance(prompt_template, dict):
        try:
            sys_p = prompt_template.get("system_prompt", "")
            user_tmplt = prompt_template.get("user_template", "")
            model_to_use = prompt_template.get("model", "gemini-3-flash-preview")

            formatted_user = user_tmplt.format(
                user_label=user_label,
                goal=goal,
                current_now=current_now,
                activities_json=activities_json
            )
            formatted_prompt = f"{sys_p}\n\n{formatted_user}"
        except Exception as e:
             print(f"[{user_label}] ⚠️ Error formatting Notion workout prompt (dict): {e}")
             formatted_prompt = None

    elif prompt_template and isinstance(prompt_template, str):
        try:
            formatted_prompt = prompt_template.format(
                user_label=user_label,
                goal=goal,
                current_now=current_now,
                activities_json=activities_json
            )
        except Exception as e:
            print(f"[{user_label}] ⚠️ Error formatting Notion workout prompt: {e}")
            formatted_prompt = None

    if formatted_prompt:
        prompt = formatted_prompt
    else:
        prompt = f"""
        Bạn là Chuyên gia phân tích dữ liệu thể thao (Sports Data Scientist) và HLV chuyên nghiệp.
        Hãy phân tích dữ liệu bài tập trong 24h qua của VĐV: {user_label}.
        Thời gian báo cáo: {current_now}
        
        MỤC TIÊU VĐV: {goal}
        
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

    # --- ROTATION LOGIC (Refactored) ---
    def worker(api_key):
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_to_use,
            contents=prompt
        )
        return response.text

    return key_manager.execute_with_retry(
        worker_func=worker,
        default_return=None,
        verbose_label=user_label
    )

def get_speech_script(original_text, user_config, prompt_template=None, mode="daily"):
    """
    Dùng Gemini để viết lại nội dung báo cáo thành kịch bản nói tự nhiên.
    """
    user_label = user_config.get('name', 'Bạn')
    print(f"[{user_label}] 🗣️ Đang viết kịch bản Voice...")
    
    context_str = "báo cáo thể thao" if mode == "daily" else "phân tích giấc ngủ sáng nay"
    
    formatted_prompt = None
    model_to_use = "gemini-3-flash-preview"

    if prompt_template and isinstance(prompt_template, dict):
        try:
             # Voice script might not need intricate splitting but consistency helps
             sys_p = prompt_template.get("system_prompt", "")
             user_tmplt = prompt_template.get("user_template", "")
             model_to_use = prompt_template.get("model", "gemini-3-flash-preview")
             
             formatted_user = user_tmplt.format(
                user_label=user_label,
                context_str=context_str,
                original_text=original_text
             )
             formatted_prompt = f"{sys_p}\n\n{formatted_user}"
        except Exception as e:
            print(f"[{user_label}] ⚠️ Error formatting Notion voice prompt (dict): {e}")
            formatted_prompt = None

    elif prompt_template and isinstance(prompt_template, str):
        try:
            formatted_prompt = prompt_template.format(
                user_label=user_label,
                context_str=context_str,
                original_text=original_text
            )
        except Exception as e:
            print(f"[{user_label}] ⚠️ Error formatting Notion voice prompt: {e}")
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

    # --- ROTATION LOGIC (Refactored) ---
    def worker(api_key):
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_to_use,
            contents=prompt
        )
        return response.text.strip()

    return key_manager.execute_with_retry(
        worker_func=worker,
        default_return="Xin chào, đây là báo cáo sức khỏe của bạn. Hãy kiểm tra tin nhắn văn bản để biết chi tiết.",
        verbose_label=user_label
    )

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
    print(f"🗣️ Đang tạo voice bằng Gemini ({voice})...")
        
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
            print(f"✅ Audio saved to {final_output_file}")
            return True
        else:
             raise Exception("Stream finished but no audio data collected.")

    return key_manager.execute_with_retry(
        worker_func=worker,
        default_return=False,
        verbose_label="Gemini TTS"
    )
