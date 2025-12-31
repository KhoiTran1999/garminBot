import os
import math
import asyncio
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
import pytz
import time
import wave
import struct
import mimetypes


# Thư viện
from garminconnect import Garmin
from telegram import Bot
from google import genai 

# Import module Notion mới tạo
from notion_db import get_users_from_notion
from google.genai import types
import base64

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

# ==============================================================================
# 3. MODULE AI ANALYST (Đã tích hợp Notion Context)
# ==============================================================================

def get_ai_advice(today, r_data, r_score, l_data, user_config):
    # Lấy thông tin cá nhân hóa từ Notion
    user_label = user_config.get('name', 'VĐV')
    goal = user_config.get('goal', 'Duy trì sức khỏe')
    injury = user_config.get('injury', 'Không có')
    note = user_config.get('note', '')

    print(f"[{user_label}] 🧠 Đang gọi AI Coach (Context: {goal} | {injury})...")
    
    if not GEMINI_API_KEY:
        return "⚠️ Lỗi: Chưa cấu hình GEMINI_API_KEY."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        activities_text = "\n".join(l_data['raw_activities_for_ai']) if l_data['raw_activities_for_ai'] else "Không có hoạt động đáng kể."
        
        vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        current_now = datetime.now(vn_timezone).strftime("%H:%M:%S, %d/%m/%Y")
        
        nap_text = f"+ Ngủ trưa: {int(r_data['nap_seconds']//60)} phút" if r_data['nap_seconds'] > 0 else ""

        # --- PROMPT KẾT HỢP NOTION ---
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

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text

    except Exception as e:
        print(f"[{user_label}] ❌ Lỗi AI: {e}")
        return "AI Coach đang bận, vui lòng thử lại sau."

def get_speech_script(original_text, user_config):
    """
    Dùng Gemini để viết lại nội dung báo cáo thành kịch bản nói tự nhiên.
    """
    user_label = user_config.get('name', 'Bạn')
    print(f"[{user_label}] 🗣️ Đang viết kịch bản Voice...")
    
    if not GEMINI_API_KEY:
        return original_text

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
        Dưới đây là một báo cáo thể thao của user {user_label}:
        ---
        {original_text}
        ---
        Hãy viết lại nội dung trên thành một kịch bản nói (Speech Script) để chuyển sang giọng đọc AI (Text-to-Speech).
        
        YÊU CẦU:
        1. Giọng văn: Thân mật, tự nhiên, như một người bạn hoặc HLV ân cần. Tránh đọc y chang các ký tự đặc biệt như dấu sao (*), gạch đầu dòng (-).
        2. Mở đầu: "Chào {user_label},..."
        3. Nội dung: Tóm tắt điểm chính về sức khỏe hôm nay, đánh giá ngắn gọn, và lời khuyên tập luyện. Đừng quá dài dòng liệt kê số liệu khô khan nếu không cần thiết.
        4. Kết thúc: Một lời chúc năng lượng.
        5. Sử dụng dấu "..." khi ngập ngừng cho lời nói chân thật hơn.
        6. Quan trọng: Chỉ trả về text thuần để đọc, không chứa Markdown hay emoji.
        """
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi Scripting: {e}")
        return "Xin chào, đây là báo cáo sức khỏe của bạn. Hãy kiểm tra tin nhắn văn bản để biết chi tiết."


def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys. Values will be
        integers if found, otherwise None.
    """
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts: # Skip the main type part
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                # Handle cases like "rate=" with no value or non-integer value
                pass # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass # Keep bits_per_sample as default if conversion fails

    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

async def generate_audio_from_text(text, output_file, voice="Puck"):
    """
    Tạo file WAV dùng Gemini TTS.
    Model: gemini-2.5-pro-preview-tts (Matching user provided snippet)
    Method: Streaming + Accumulation + Manual WAV Header
    """
    print(f"🗣️ Đang tạo voice bằng Gemini ({voice})...")
    if not GEMINI_API_KEY:
        return False
        
    retries = 3
    for attempt in range(retries):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=text),
                    ],
                ),
            ]
            
            # Config matching user snippet
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
            
            # STRICTLY using the model from the user's snippet
            model_name = "gemini-2.5-flash-preview-tts"
            
            print(f"   Model: {model_name} | Streaming...")
            
            all_raw_bytes = bytearray()
            mime_type = None

            # Stream loop matching user snippet structure
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
                    # Capture mime for header generation
                    if not mime_type:
                        mime_type = part.inline_data.mime_type
                    
                    # Store raw PCM data
                    all_raw_bytes.extend(part.inline_data.data)

            if len(all_raw_bytes) > 0:
                 # Default mime if missing
                if not mime_type:
                    mime_type = "audio/L16;rate=24000"
                
                # Convert FINAL accumulated raw bytes to WAV
                # Note: We do this ONCE for the whole file, not per chunk.
                wav_data = convert_to_wav(all_raw_bytes, mime_type)

                # Ensure output file ends with .wav
                if not output_file.lower().endswith(".wav"):
                     output_file = output_file.rsplit('.', 1)[0] + ".wav"
                
                # Write to file
                try:
                    with open(output_file, "wb") as f:
                        f.write(wav_data)
                    print(f"✅ Audio saved to {output_file} (Total wrapped Size: {len(wav_data)} bytes)")
                    return True
                except Exception as e:
                     print(f"❌ Error writing file: {e}")
                     return False
            else:
                print("❌ Stream finished. No audio data collected.")
                return False

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait_time = 40 * (attempt + 1)
                print(f"⚠️ Quota Exceeded. Retrying in {wait_time}s... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                print(f"❌ Lỗi Gemini TTS: {e}")
                return False
                
    return False

# ==============================================================================
# 4. MODULE TELEGRAM & MAIN FLOW
# ==============================================================================

async def send_telegram_report(message, chat_id, user_label="User", audio_path=None):
    print(f"[{user_label}] 📲 Đang gửi Telegram...")
    if not TELE_TOKEN or not chat_id:
        print(f"[{user_label}] ⚠️ Không có Chat ID hoặc Token.")
        return

    bot = Bot(token=TELE_TOKEN)
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"[{user_label}] ✅ Gửi thành công!")
    except Exception as e:
        print(f"[{user_label}] ⚠️ Lỗi Markdown, đang gửi Plain Text...")
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
        except Exception as e2:
            print(f"❌ Lỗi gửi tin nhắn: {e2}")

    # Gửi Voice nếu có
    if audio_path and os.path.exists(audio_path):
        print(f"[{user_label}] 🎙️ Đang gửi Voice Note...")
        try:
            with open(audio_path, 'rb') as audio:
                await bot.send_voice(chat_id=chat_id, voice=audio, caption="🎧 Voice Coach")
            print(f"[{user_label}] ✅ Gửi Voice thành công!")
        except Exception as e:
            print(f"[{user_label}] ⚠️ Lỗi gửi Voice: {e}")

async def process_single_user(user_config):
    # Lấy thông tin từ object user của Notion
    name = user_config.get('name', 'Unknown')
    email = user_config.get('email')
    password = user_config.get('password')
    tele_id = user_config.get('telegram_chat_id')

    if not email or not password: 
        print(f"[{name}] ❌ Thiếu Email/Pass, bỏ qua.")
        return

    try:
        client = Garmin(email, password)
        client.login()
        print(f"[{name}] ✅ Đăng nhập Garmin thành công.")
        
        today = date.today()
        # today = date(2025, 12, 30) # Dùng khi test ngày cũ

        # 1. Lấy dữ liệu Garmin (Sleep + Stats)
        r_data, r_score, l_data = get_processed_data(client, today, name)

        # 2. Gọi AI (Truyền cả user_config chứa Goal/Injury từ Notion)
        ai_report = get_ai_advice(today, r_data, r_score, l_data, user_config)

        # 3. Tạo Voice Script & Audio
        speech_script = get_speech_script(ai_report, user_config)
        
        audio_file = f"voice_{name}_{today}.wav"
        has_audio = await generate_audio_from_text(speech_script, audio_file)
        
        # 4. Gửi Telegram (Kèm Audio)
        if tele_id:
            await send_telegram_report(ai_report, tele_id, name, audio_file if has_audio else None)
        else:
            print(f"[{name}] ⚠️ Không có Chat ID, không gửi tin.")
        
        # Xóa file audio tạm
        if has_audio and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except: pass
            
    except Exception as e:
        print(f"[{name}] ❌ Lỗi xử lý: {e}")

async def main():
    print("=== GARMIN AI COACH PRO (NOTION INTEGRATED) ===")
    
    # Lấy danh sách user từ Notion thay vì biến môi trường cũ
    users = get_users_from_notion()
    
    if not users:
        print("⚠️ Không tìm thấy user nào Active trên Notion.")
        return

    print(f"🚀 Kích hoạt quy trình cho {len(users)} người dùng...")
    
    tasks = [process_single_user(user) for user in users]
    await asyncio.gather(*tasks)
    print("\n=== HOÀN TẤT ===")

if __name__ == "__main__":
    asyncio.run(main())