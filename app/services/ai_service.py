import os
import pytz
import time
import struct
import random
from datetime import datetime
from typing import Optional, Dict
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class GeminiKeyManager:
    """
    Quản lý danh sách API Key và xoay vòng (Round Robin) + Failover.
    """
    def __init__(self):
        self.keys = []
        self._load_keys()
        self.current_index = 0

    def _load_keys(self):
        # 1. Load key chính
        main_key = os.getenv("GEMINI_API_KEY")
        if main_key:
            self.keys.append(main_key)
        
        # 2. Load các key phụ (GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...)
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key:
                self.keys.append(key)
                i += 1
            else:
                break
        
        if not self.keys:
            print("⚠️ CẢNH BÁO: Không tìm thấy GEMINI_API_KEY nào trong .env!")
        else:
            print(f"🔑 Đã load {len(self.keys)} Gemini API Keys.")

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

# Khởi tạo Global Instance
key_manager = GeminiKeyManager()

def get_ai_advice(today, r_data, r_score, l_data, user_config, mode="daily"):
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

    if mode == "sleep_analysis":
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

    # --- CƠ CHẾ XOAY VÒNG KEY & RETRY ---
    max_attempts = key_manager.get_key_count() * 2 # Thử gấp đôi số key để chắc chắn
    if max_attempts == 0: return "⚠️ Lỗi: Không tìm thấy GEMINI_API_KEY nào."

    for attempt in range(max_attempts):
        current_api_key = key_manager.get_current_key()
        try:
            client = genai.Client(api_key=current_api_key)
            response = client.models.generate_content(
                model="gemini-3-flash-preview", # Upscale model luôn
                contents=prompt
            )
            # Thành công -> Rotate một cái để lần sau dùng key khác (Load balancing)
            key_manager.rotate_key()
            return response.text

        except Exception as e:
            error_msg = str(e)
            print(f"[{user_label}] ⚠️ Lỗi AI (Key ending ...{current_api_key[-5:] if current_api_key else 'None'}): {error_msg}")
            
            # Xử lý các lỗi cần đổi key
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                print(f"   --> Quota Exceeded. Rotating key...")
                key_manager.rotate_key()
                time.sleep(1) # Nghỉ nhẹ 1s
            else:
                # Lỗi không phải quota (vd 500, network) -> Cũng thử rotate tiếp xem sao
                key_manager.rotate_key()
                time.sleep(2)

    return "AI Coach đang bận hoặc hết Quota tất cả các key. Vui lòng thử lại sau."

def get_workout_analysis_advice(activity_data_list, user_config):
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

    # --- ROTATION LOGIC ---
    max_attempts = key_manager.get_key_count() * 2
    if max_attempts == 0: return None

    for attempt in range(max_attempts):
        current_api_key = key_manager.get_current_key()
        try:
            client = genai.Client(api_key=current_api_key)
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            key_manager.rotate_key()
            return response.text
        except Exception as e:
            error_msg = str(e)
            print(f"[{user_label}] ⚠️ Lỗi AI Workout (Key ...{current_api_key[-5:]}): {error_msg}")
            key_manager.rotate_key()
            time.sleep(1)

    return None

def get_speech_script(original_text, user_config, mode="daily"):
    """
    Dùng Gemini để viết lại nội dung báo cáo thành kịch bản nói tự nhiên.
    """
    user_label = user_config.get('name', 'Bạn')
    print(f"[{user_label}] 🗣️ Đang viết kịch bản Voice...")
    
    context_str = "báo cáo thể thao" if mode == "daily" else "phân tích giấc ngủ sáng nay"
    
    prompt = f"""
    Bạn là người bạn thân và cũng là trợ lý trong công việc của {user_label}.
    Dưới đây là một {context_str} của họ:
    ---
    {original_text}
    ---        
    Nhiệm vụ: Viết lại thành **KỊCH BẢN ĐỌC (Voice Script)** ngắn gọn, tự nhiên, bỏ emoji, bỏ markdown. Giọng điệu: Hào hứng, năng động, ấm áp, như một người bạn đồng hành.
    """

    # --- ROTATION LOGIC ---
    max_attempts = key_manager.get_key_count() * 2
    if max_attempts == 0: return original_text

    for attempt in range(max_attempts):
        current_api_key = key_manager.get_current_key()
        try:
            client = genai.Client(api_key=current_api_key)
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            key_manager.rotate_key()
            return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            print(f"[{user_label}] ⚠️ Lỗi Scripting (Key ...{current_api_key[-5:]}): {error_msg}")
            key_manager.rotate_key()
            time.sleep(1)
    
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

    # --- ROTATION LOGIC for TTS ---
    max_attempts = key_manager.get_key_count() * 2
    if max_attempts == 0: return False

    for attempt in range(max_attempts):
        current_api_key = key_manager.get_current_key()
        try:
            client = genai.Client(api_key=current_api_key)
            
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
                if not mime_type: mime_type = "audio/L16;rate=24000"
                wav_data = convert_to_wav(all_raw_bytes, mime_type)

                if not output_file.lower().endswith(".wav"):
                        output_file = output_file.rsplit('.', 1)[0] + ".wav"
                
                try:
                    with open(output_file, "wb") as f:
                        f.write(wav_data)
                    print(f"✅ Audio saved to {output_file}")
                    
                    # Thành công -> Rotate cho lần sau
                    key_manager.rotate_key()
                    return True
                except Exception as e:
                        print(f"❌ Error writing file: {e}")
                        # Lỗi write file thì không cần đổi key, nhưng cứ return False
                        return False
            else:
                print("❌ Stream finished. No audio data collected.")
                # Có thể do lỗi API trả về stream rỗng -> thử key khác
                key_manager.rotate_key()
                continue # Retry next key

        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Lỗi Gemini TTS (Key ...{current_api_key[-5:]}): {error_msg}")
            
            # Logic retry tương tự
            key_manager.rotate_key()
            time.sleep(2)
                
    return False
