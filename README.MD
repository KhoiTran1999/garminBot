# 🏃‍♂️ Garmin AI Coach Pro (Web Dashboard & Vercel Deployed)

**Trợ lý ảo Huấn luyện viên chạy bộ cá nhân hóa, sử dụng dữ liệu Garmin Connect, Google Gemini AI, quản lý ngữ cảnh qua Notion và hiển thị trực quan trên Website Vercel.**

Dự án này tự động hóa quy trình thu thập dữ liệu sức khỏe từ Garmin Connect, tính toán các chỉ số chuyên sâu (Training Readiness, TRIMP Banister, Acute Load), kết hợp với **ngữ cảnh cá nhân từ Notion** (Mục tiêu, Chấn thương) để đưa ra giáo án tập luyện, phân tích chuyên sâu và bản thu âm giọng nói (Voice Coach) trên giao diện Web hiện đại.

---

## ✨ Tính năng nổi bật

* **🌐 Web Dashboard Hiện đại (Mới trên Vercel):**
    * Giao diện thể thao tối ưu cho cả Điện thoại & Máy tính (Next.js 15, Tailwind CSS, Lucide Icons).
    * Đăng nhập độc lập an toàn bằng Email & Mật khẩu đồng bộ với danh sách vận động viên trên Notion.
    * Kích hoạt phân tích tức thì 1-chạm:
        * 📊 **Sức khỏe & Đề xuất tập (Daily):** Tính điểm sẵn sàng, tải 7 ngày, AQI và bài chạy hôm nay.
        * 💤 **Phân tích Giấc ngủ (Sleep):** Mổ xẻ chi tiết 3 pha ngủ (Deep, Light, REM), RHR, SpO2.
        * 🏃 **Phân tích Bài tập (Workout):** Splits theo km, phân bổ vùng nhịp tim, Cardiac Drift.
        * 🔋 **Bắt mạch Năng lượng (Battery):** Body Battery & Stress rút gọn 2h/block.
    * 🎙️ **Trình phát âm thanh Voice Coach:** Nghe trực tiếp bản thu âm AI giọng đọc huấn luyện viên trên web.
    * 💬 **Phòng Chat AI Coach 2 chiều:** Trò chuyện hỏi đáp với HLV, tự động tra cứu dữ liệu sức khỏe Garmin qua Tool Calling.
    * 📝 **Hồ sơ Vận động viên:** Chỉnh sửa Mục tiêu chạy bộ & Chấn thương, đồng bộ 2 chiều tức thì lên Notion Database.

* **☁️ Triển khai Serverless Toàn diện trên Vercel:**
    * Chạy toàn bộ Next.js Frontend và Python FastAPI Serverless Backend (`api/index.py`) trên cùng một dự án Vercel.
    * Cấu hình mở rộng `maxDuration: 60` trong `vercel.json`.

* **📲 Kênh Thông báo Tùy chọn qua Telegram:**
    * Vẫn duy trì khả năng nhận báo cáo đẩy tự động hàng ngày qua Telegram Bot (GitHub Actions CRON).

---

## 🛠️ Yêu cầu chuẩn bị

1. **Tài khoản Garmin Connect:** Email và Mật khẩu.
2. **Google Gemini API Key** hoặc **9Router API Key** (cho LLM & TTS).
3. **Notion Integration:**
    * Database User: `NOTION_DATABASE_ID` (gồm các cột: Name, Email, Password, Active, Training Goal, Chấn thương & Bệnh tật, Ghi chú, Telegram Chat ID).
    * Database Prompt: `NOTION_PROMPT_DATABASE_ID`.
    * `NOTION_TOKEN`.
4. **Redis:** (Upstash hoặc Redis Cloud) để lưu lịch sử chat, cache báo cáo và rate limit.
5. **Tài khoản Vercel:** Để deploy Website.

---

## 🚀 Chạy Thử nghiệm (Local Development)

### 1. Cài đặt Dependencies:
```bash
# Cài đặt Python packages (FastAPI, Garmin, Gemini, etc.)
pip install -r requirements.txt

# Cài đặt Node.js packages (Next.js, Tailwind, etc.)
npm install
```

### 2. Cấu hình biến môi trường (`.env`):
```env
# Notion
NOTION_TOKEN="secret_xxx"
NOTION_DATABASE_ID="xxx"
NOTION_PROMPT_DATABASE_ID="xxx"

# AI
GEMINI_API_KEY="xxx"
ROUTER9_API_KEY="xxx"

# Redis & JWT
REDIS_URL="rediss://default:xxx@host:port"
JWT_SECRET="your-super-secret-jwt-key"
```

### 3. Khởi chạy song song Frontend & Backend:
- **Terminal 1 (Python FastAPI Backend):**
  ```bash
  uvicorn api.index:app --reload --port 8000
  ```
- **Terminal 2 (Next.js Frontend):**
  ```bash
  npm run dev
  ```
- Mở trình duyệt và truy cập `http://localhost:3000` để trải nghiệm!

---

## 🚀 Triển khai (Deploy) lên Vercel

1. **Đẩy mã nguồn lên GitHub.**
2. Truy cập [vercel.com](https://vercel.com) > **Add New Project** > Chọn kho lưu trữ `garminBot`.
3. Trong mục **Environment Variables**, cấu hình các biến từ file `.env`:
   - `NOTION_TOKEN`
   - `NOTION_DATABASE_ID`
   - `NOTION_PROMPT_DATABASE_ID`
   - `GEMINI_API_KEY` (và `GEMINI_API_KEY_1`, `2`, `3` nếu có)
   - `ROUTER9_API_KEY`
   - `REDIS_URL`
   - `JWT_SECRET`
4. Bấm **Deploy**. Vercel sẽ tự động build ứng dụng Next.js và triển khai Python serverless function tại `/api`!