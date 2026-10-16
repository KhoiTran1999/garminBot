import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import jwt
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# Thiết lập đường dẫn import gốc để nhận app.services và app.config
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import Config
from backend.services.notion_service import get_users_from_notion
from backend.services.garmin_service import (
    get_processed_data,
    fetch_daily_activities_detailed,
    check_garmin_sync_status,
)
from backend.services.ai_service import (
    get_ai_advice,
    get_workout_analysis_advice,
    get_battery_analysis_advice,
    get_speech_script,
    generate_audio_from_text,
    get_customer_service_advice,
    stream_customer_service_advice,
)
from backend.services.prompt_service import get_prompts_from_notion
from backend.services.weather_service import WeatherService
from backend.services.redis_service import redis_service

app = FastAPI(title="Garmin AI Coach Pro API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import tempfile

JWT_SECRET = os.getenv("JWT_SECRET", "garmin-ai-coach-super-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 60

# Trên Vercel Serverless, hệ thống file /var/task là read-only.
# Chỉ có /tmp (tempfile.gettempdir()) là có quyền ghi.
AUDIO_DIR = os.path.join(tempfile.gettempdir(), "audio")
try:
    os.makedirs(AUDIO_DIR, exist_ok=True)
except Exception as dir_err:
    print(f"Warning creating audio dir: {dir_err}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Lỗi máy chủ nội bộ: {str(exc)}"}
    )


# --- Pydantic Schemas ---
class LoginRequest(BaseModel):
    email: str
    password: str

class RunAnalysisRequest(BaseModel):
    mode: str  # daily | sleep_analysis | workout | battery
    user_note: Optional[str] = None

class ChatRequest(BaseModel):
    question: str
    stream: Optional[bool] = True

class ProfileUpdateRequest(BaseModel):
    goal: Optional[str] = None
    injury: Optional[str] = None
    note: Optional[str] = None

# --- Helper Garmin Login ---
def login_garmin_for_web(user: dict):
    from main import login_garmin
    email = user.get("email")
    password = user.get("password")
    name = user.get("name", "User")
    return login_garmin(email, password, name)

# --- JWT Helpers ---
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập (Thiếu Bearer Token)"
        )
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn hoặc không hợp lệ")

    # 1. Kiểm tra nhanh trong Redis cache (< 5ms, không phụ thuộc Notion network)
    cached_user = redis_service.get_user_cache(email)
    if cached_user:
        return cached_user

    # 2. Tra cứu Notion nếu chưa có trong Redis cache
    try:
        users = get_users_from_notion()
        for u in users:
            if u.get("email", "").strip().lower() == email.strip().lower():
                redis_service.set_user_cache(email, u, ttl_seconds=86400 * 60)
                return u
    except Exception as e:
        print(f"Lỗi khi tra cứu Notion cho user {email}: {e}")

    # 3. Fallback an toàn từ JWT payload để người dùng không bao giờ bị văng đăng nhập đột ngột
    if payload.get("sub"):
        fallback_user = {
            "email": payload.get("sub"),
            "name": payload.get("name", "Vận động viên"),
            "goal": payload.get("goal", ""),
            "injury": payload.get("injury", ""),
            "note": payload.get("note", ""),
            # Giữ password nếu có lưu trong cache trước đó
            "password": ""
        }
        redis_service.set_user_cache(email, fallback_user, ttl_seconds=86400 * 60)
        return fallback_user

    raise HTTPException(status_code=404, detail="Không tìm thấy người dùng trong hệ thống Notion")

# --- Routes ---

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Garmin AI Coach Pro Web Backend",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/auth/login")
def login(req: LoginRequest):
    target_user = None

    # 1. Tìm user trong Notion
    try:
        users = get_users_from_notion()
        for u in users:
            if u.get("email", "").strip().lower() == req.email.strip().lower():
                if u.get("password", "").strip() == req.password.strip():
                    target_user = u
                    break
    except Exception as e:
        print(f"Lỗi khi kiểm tra Notion khi login: {e}")

    # 2. Fallback kiểm tra Redis cache nếu Notion tạm thời chậm/lỗi
    if not target_user:
        cached = redis_service.get_user_cache(req.email)
        if cached and cached.get("password", "").strip() == req.password.strip():
            target_user = cached

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác, hoặc tài khoản chưa kích hoạt trên Notion."
        )

    # Lưu user vào Redis cache với TTL 60 ngày
    redis_service.set_user_cache(target_user["email"], target_user, ttl_seconds=86400 * 60)

    token = create_access_token({
        "sub": target_user["email"],
        "name": target_user.get("name", "Vận động viên"),
        "goal": target_user.get("goal", ""),
        "injury": target_user.get("injury", ""),
        "note": target_user.get("note", "")
    })
    return {
        "token": token,
        "user": {
            "name": target_user.get("name"),
            "email": target_user.get("email"),
            "goal": target_user.get("goal"),
            "injury": target_user.get("injury"),
            "note": target_user.get("note")
        }
    }

@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return {
        "user": {
            "name": user.get("name"),
            "email": user.get("email"),
            "goal": user.get("goal"),
            "injury": user.get("injury"),
            "note": user.get("note")
        }
    }

@app.get("/api/garmin/status")
def get_garmin_status(user: dict = Depends(get_current_user)):
    try:
        client = login_garmin_for_web(user)
        is_fresh, fresh_msg = check_garmin_sync_status(client, max_age_hours=2.0, user_label=user.get("name"))
        return {
            "is_fresh": is_fresh,
            "message": fresh_msg
        }
    except Exception as e:
        return {
            "is_fresh": False,
            "message": f"Không thể kết nối Garmin: {str(e)}"
        }

@app.get("/api/overview")
def get_dashboard_overview(user: dict = Depends(get_current_user)):
    """
    Trả về dữ liệu tổng quan cho trang chủ (Dashboard).
    Bao gồm các báo cáo gần nhất từ Redis và trạng thái hồ sơ.
    """
    email = user.get("email")
    name = user.get("name")
    
    # Lấy các báo cáo gần đây từ Redis cache
    latest_daily = redis_service.get_ai_context(email, "daily", limit=1)
    latest_sleep = redis_service.get_ai_context(email, "sleep_analysis", limit=1)
    latest_workout = redis_service.get_ai_context(email, "workout", limit=1)
    latest_battery = redis_service.get_ai_context(email, "battery", limit=1)

    aqi_data = WeatherService.get_aqi_data()

    return {
        "user": {
            "name": name,
            "email": email,
            "goal": user.get("goal"),
            "injury": user.get("injury")
        },
        "weather": aqi_data,
        "recent_reports": {
            "daily": latest_daily[0] if latest_daily else None,
            "sleep": latest_sleep[0] if latest_sleep else None,
            "workout": latest_workout[0] if latest_workout else None,
            "battery": latest_battery[0] if latest_battery else None
        }
    }

@app.post("/api/analysis/run")
async def run_analysis(req: RunAnalysisRequest, user: dict = Depends(get_current_user)):
    """
    Kích hoạt phân tích On-Demand cho các mode:
    daily | sleep_analysis | workout | battery
    """
    name = user.get("name", "User")
    email = user.get("email")
    today = date.today()
    mode = req.mode

    if mode not in ["daily", "sleep_analysis", "workout", "battery"]:
        raise HTTPException(status_code=400, detail=f"Mode '{mode}' không hợp lệ.")

    try:
        client = login_garmin_for_web(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đăng nhập Garmin Connect: {str(e)}")

    is_fresh, fresh_msg = check_garmin_sync_status(client, max_age_hours=2.0, user_label=name)
    prompts = get_prompts_from_notion(use_cache=True)
    aqi_data = WeatherService.get_aqi_data()

    ai_report = ""
    r_score = None

    try:
        if mode in ["daily", "sleep_analysis"]:
            r_data, r_score, l_data = get_processed_data(client, today, name)
            prompt_key = "sleep_analysis" if mode == "sleep_analysis" else "daily_report"
            template = prompts.get(prompt_key)
            ai_report = get_ai_advice(
                today, r_data, r_score, l_data, user,
                prompt_template=template, mode=mode,
                aqi_data=aqi_data, user_note=req.user_note
            )

        elif mode == "workout":
            activities = fetch_daily_activities_detailed(client, today, name)
            if not activities:
                return {
                    "status": "warning",
                    "mode": mode,
                    "report": "Hôm nay bạn chưa có hoạt động chạy bộ nào được ghi nhận trên Garmin Connect để phân tích.",
                    "audio_url": None,
                    "metrics": {"is_fresh": is_fresh, "fresh_msg": fresh_msg}
                }
            workout_template = prompts.get("workout_analysis")
            ai_report = get_workout_analysis_advice(
                activities, user,
                prompt_template=workout_template,
                aqi_data=aqi_data, user_note=req.user_note
            )

        elif mode == "battery":
            r_data, r_score, l_data = get_processed_data(client, today, name)
            battery_template = prompts.get("battery_analysis")
            ai_report = get_battery_analysis_advice(
                today, r_data, user,
                prompt_template=battery_template,
                aqi_data=aqi_data, user_note=req.user_note
            )

        # Lưu báo cáo vào Redis để làm AI Context và hiển thị lịch sử
        if ai_report:
            redis_service.save_ai_context(email, mode, ai_report, limit=5)

        # Tạo Voice Script & File Audio WAV
        audio_filename = f"voice_{name.replace(' ', '_')}_{mode}_{today}.wav"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        
        has_audio = False
        try:
            voice_template = prompts.get("voice_script")
            speech_script = get_speech_script(ai_report, user, prompt_template=voice_template, mode=mode)
            has_audio = await generate_audio_from_text(speech_script, audio_path)
        except Exception as audio_err:
            print(f"[{name}] ⚠️ Lỗi tạo audio: {audio_err}")

        return {
            "status": "success",
            "mode": mode,
            "report": ai_report,
            "audio_url": f"/api/audio/{audio_filename}" if has_audio else None,
            "metrics": {
                "readiness_score": r_score,
                "is_fresh": is_fresh,
                "fresh_msg": fresh_msg,
                "date": today.isoformat()
            }
        }

    except Exception as run_err:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý phân tích AI ({mode}): {str(run_err)}")

@app.get("/api/audio/{filename}")
def get_audio_file(filename: str):
    safe_filename = os.path.basename(filename)
    audio_path = os.path.join(AUDIO_DIR, safe_filename)
    if not os.path.exists(audio_path):
        public_audio = os.path.join(ROOT_DIR, "public", "audio", safe_filename)
        root_audio = os.path.join(ROOT_DIR, safe_filename)
        if os.path.exists(public_audio):
            audio_path = public_audio
        elif os.path.exists(root_audio):
            audio_path = root_audio
        else:
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp âm thanh.")

    return FileResponse(audio_path, media_type="audio/wav")

@app.get("/api/chat/history")
def get_chat_history(user: dict = Depends(get_current_user)):
    user_id = user.get("email")
    history = redis_service.get_chat_history(user_id, limit=20)
    return {"history": history}

@app.post("/api/chat")
async def chat_with_coach(req: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        user_id = user.get("email")
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

        prompts = get_prompts_from_notion(use_cache=True)
        ask_template = prompts.get("ask_help")

        # Lazy Garmin client: chỉ đăng nhập khi AI thực sự gọi Garmin tools.
        client_instance = None
        def get_garmin_client():
            nonlocal client_instance
            if client_instance is None:
                try:
                    client_instance = login_garmin_for_web(user)
                except Exception as ge:
                    print(f"[{user.get('name')}] Warning Garmin client chat: {ge}")
            return client_instance

        # 1. Trả về dạng JSON tĩnh nếu client yêu cầu stream=False
        if req.stream is False:
            ai_reply = await get_customer_service_advice(
                user_id=user_id,
                question=question,
                user_config=user,
                prompt_template=ask_template,
                garmin_client=get_garmin_client
            )
            return {"reply": ai_reply or "Không nhận được phản hồi từ AI. Vui lòng thử lại."}

        # 2. Mặc định: Trả về Streaming SSE kèm cập nhật tiến trình (status) và từng chunk (token stream)
        import json
        async def sse_generator():
            try:
                async for event in stream_customer_service_advice(
                    user_id=user_id,
                    question=question,
                    user_config=user,
                    prompt_template=ask_template,
                    garmin_client=get_garmin_client
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as stream_err:
                print(f"[{user.get('name')}] SSE Stream Error: {stream_err}")
                err_payload = {"type": "error", "message": f"Lỗi luồng xử lý AI: {str(stream_err)}"}
                yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[{user.get('name', 'User')}] Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý chat: {str(e)}")

@app.post("/api/profile/update")
def update_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    """
    Cập nhật Mục tiêu (Goal), Chấn thương (Injury), hoặc Ghi chú vào Notion.
    """
    token = Config.NOTION_TOKEN
    database_id = Config.NOTION_DATABASE_ID

    if not token or not database_id:
        raise HTTPException(status_code=500, detail="Thiếu cấu hình Notion Token.")

    # Tìm Page ID của user trong Notion
    url_query = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    page_id = None
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url_query, headers=headers, json={
                "filter": {
                    "property": "Email",
                    "email": {"equals": user.get("email")}
                }
            })
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    page_id = results[0]["id"]
    except Exception as q_err:
        raise HTTPException(status_code=500, detail=f"Lỗi tìm user trong Notion: {q_err}")

    if not page_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi User trên Notion.")

    # Cập nhật Properties
    properties = {}
    if req.goal is not None:
        properties["Training Goal"] = {
            "rich_text": [{"type": "text", "text": {"content": req.goal}}]
        }
    if req.injury is not None:
        properties["Chấn thương & Bệnh tật"] = {
            "rich_text": [{"type": "text", "text": {"content": req.injury}}]
        }
    if req.note is not None:
        properties["Ghi chú"] = {
            "rich_text": [{"type": "text", "text": {"content": req.note}}]
        }

    try:
        with httpx.Client(timeout=10.0) as client:
            update_url = f"https://api.notion.com/v1/pages/{page_id}"
            up_resp = client.patch(update_url, headers=headers, json={"properties": properties})
            if up_resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Lỗi cập nhật Notion: {up_resp.text}")
    except Exception as patch_err:
        raise HTTPException(status_code=500, detail=f"Lỗi gửi dữ liệu lên Notion: {patch_err}")

    return {
        "status": "success",
        "message": "Cập nhật hồ sơ trên Notion thành công!"
    }
