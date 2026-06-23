# 🏃‍♂️ Garmin AI Coach Pro (Notion Integrated)

**Trợ lý ảo Huấn luyện viên chạy bộ cá nhân hóa, sử dụng dữ liệu Garmin, Google Gemini AI và quản lý qua Notion.**

Dự án này tự động hóa quy trình thu thập dữ liệu sức khỏe từ Garmin Connect, tính toán các chỉ số chuyên sâu (Training Readiness, TRIMP), kết hợp với **ngữ cảnh cá nhân từ Notion** (Mục tiêu, Chấn thương) để đưa ra lời khuyên tập luyện hàng ngày qua Telegram.

## ✨ Tính năng nổi bật

* **⚡ On-Demand Trigger (Mới):**
    * Tích hợp Telegram Bot với nút bấm điều khiển (Dashboard) trực quan.
    * Chat lệnh trực tiếp trên Telegram để kích hoạt phân tích ngay lập tức (`/daily`, `/sleep`, `/workout`, `/battery`).
    * Sử dụng **Cloudflare Workers** (Serverless) làm cầu nối Webhook siêu tốc, định tuyến lệnh gọi tới GitHub Actions, không cần treo máy tính 24/7.

* **🧠 Notion Database Integration:**
    * Quản lý danh sách người dùng, mật khẩu và trạng thái Active trực quan trên Notion.
    * Quản lý **System Prompts** cho AI ngay trên Notion.
    * **Cá nhân hóa theo thời gian thực:** Cập nhật "Mục tiêu" hoặc "Tình trạng chấn thương" trên Notion, AI sẽ tự động điều chỉnh giáo án ngay lập tức.

* **📊 Phân tích Dữ liệu Chuyên sâu:**
    * **Giấc ngủ:** Phân tích chi tiết 3 giai đoạn (Deep, Light, REM) và thời gian ngủ thực tế (trừ lúc tỉnh giấc).
    * **Training Readiness:** Tính điểm sẵn sàng dựa trên Pin cơ thể (Body Battery), Stress và Giấc ngủ.
    * **Acute Training Load (7 ngày):** Tính toán tải tập luyện dựa trên nhịp tim (TRIMP Banister).
    * **Chất lượng không khí (AQI):** Tích hợp thông tin thời tiết vào lời khuyên chạy bộ.

* **🤖 AI Coach (9Router/Gemini):** 
    * Sử dụng endpoint 9Router tuỳ chỉnh (với model `gemini-3.1-pro`).
    * Đóng vai HLV chuyên nghiệp, đưa ra bài tập cụ thể (Pace, Thời gian) dựa trên thể trạng thực tế.
    * Tự động tạo **Voice Script** (Text-to-Speech) để gửi lời nhắn động viên bằng giọng nói qua Telegram.
    * Hiển thị trạng thái phân tích theo thời gian thực ("Đang lấy báo cáo...", "Đang tạo bản thu âm...").

* **☁️ Tự động hóa 100%:** Chạy hoàn toàn miễn phí trên nền tảng GitHub Actions (CRON) và Cloudflare Workers.

## 🛠️ Yêu cầu chuẩn bị

Để chạy dự án, bạn cần:

1.  **Tài khoản Garmin Connect:** Email và Mật khẩu.
2.  **9Router API Key:** Lấy key 9Router (hoặc sử dụng server riêng).
3.  **Telegram Bot:** Token và Chat ID (lấy từ @BotFather và @userinfobot).
4.  **Notion Integration:**
    * Tạo Database trên Notion.
    * Lấy `NOTION_TOKEN`, `NOTION_DATABASE_ID` (User DB) và `NOTION_PROMPT_DATABASE_ID` (Prompt DB).
5.  **Cloudflare Account (Free):** Tạo Worker làm Webhook Trigger.
6.  **GitHub Account:** Để lưu trữ mã nguồn và chạy Actions.

## 🗂️ Cấu trúc Database trên Notion (User)

Bạn cần tạo một Database trên Notion với các cột chính xác như sau để Code hoạt động:

| Tên Cột (Property)          | Loại (Type) | Mô tả                                                 |
| --------------------------- | ----------- | ----------------------------------------------------- |
| **Name** | Title       | Tên hiển thị của VĐV.                                 |
| **Email** | Email       | Email đăng nhập Garmin.                               |
| **Password** | Text        | Mật khẩu Garmin (Có thể dùng token GitHub Secret).    |
| **Telegram Chat ID** | Text        | ID chat Telegram (Dạng Text để tránh lỗi format số).  |
| **Training Goal** | Text        | VD: "Marathon Sub 4", "Chạy dưỡng sinh".              |
| **Chấn thương & Bệnh tật** | Text        | VD: "Đau gối phải", "Đang ốm".                        |
| **Ghi chú** | Text        | Ghi chú thêm cho AI.                                  |
| **Active** | Checkbox    | Tick ✅ để bật Bot cho user này.                        |

> **Lưu ý:** Sau khi tạo Database, hãy nhớ cấp quyền cho Bot truy cập bằng cách bấm vào `...` > `Connections` > `Connect to` > Chọn Integration của bạn.

## 🚀 Cài đặt & Chạy (Local)

1.  **Clone repository:**
    ```bash
    git clone https://github.com/khoitran1999/garminbot.git
    cd garminbot
    ```

2.  **Cài đặt thư viện:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Cấu hình biến môi trường (`.env`):**
    ```env
    TELEGRAM_TOKEN="your_tele_token"
    ROUTER9_API_KEY="your_router9_key"
    NOTION_TOKEN="secret_your_notion_token"
    NOTION_DATABASE_ID="your_database_id"
    NOTION_PROMPT_DATABASE_ID="your_prompt_database_id"
    ```

4.  **Chạy thử nghiệm:**
    * Báo cáo hàng ngày: `python main.py --mode daily`
    * Phân tích giấc ngủ: `python main.py --mode sleep_analysis`
    * Phân tích bài tập: `python main.py --mode workout`
    * Bắt mạch năng lượng: `python main.py --mode battery`

## ⚙️ Triển khai trên GitHub Actions & Cloudflare Workers

Hệ thống hoạt động theo luồng: **Telegram -> Cloudflare Worker -> GitHub Actions -> Telegram**.

### Bước 1: Thiết lập GitHub Actions
1. Fork dự án về GitHub.
2. Vào **Settings** > **Secrets and variables** > **Actions** thêm các Secret từ file `.env` (Bao gồm cả token Garmin nếu dùng cache: `GARMINTOKENS_EMAIL_GMAIL_COM`).
3. Đảm bảo file `.github/workflows/telegram_trigger.yml` đang bật.

### Bước 2: Thiết lập Cloudflare Worker (Webhook)
1. Đăng nhập Cloudflare > **Workers & Pages** > **Create Worker**.
2. Dán nội dung file `cloudflare_worker.js` vào trình soạn thảo.
3. Vào **Settings** > **Variables and Secrets**, thêm:
    * `GITHUB_TOKEN`: Token truy cập GitHub (Classic) có quyền `repo`.
    * `TG_BOT_TOKEN`: Token Telegram Bot.
    * `NOTION_TOKEN`, `NOTION_DATABASE_ID`: Để Worker xác thực User ngay lúc chat.
    * `GITHUB_OWNER`, `GITHUB_REPO`: Thông tin kho lưu trữ GitHub của bạn.
4. Triển khai (Deploy) Worker và copy đường dẫn `*.workers.dev`.

### Bước 3: Đăng ký Webhook với Telegram
Mở trình duyệt và truy cập URL sau (Thay `BOT_TOKEN` và `WORKER_URL`):
`https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<WORKER_URL>`

Xong! Mở Telegram, chat `/start` với Bot và tận hưởng!