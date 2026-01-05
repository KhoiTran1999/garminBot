# 🏃‍♂️ Garmin AI Coach Pro (Notion Integrated)

**Trợ lý ảo Huấn luyện viên chạy bộ cá nhân hóa, sử dụng dữ liệu Garmin, Google Gemini AI và quản lý qua Notion.**

Dự án này tự động hóa quy trình thu thập dữ liệu sức khỏe từ Garmin Connect, tính toán các chỉ số chuyên sâu (Training Readiness, TRIMP), kết hợp với **ngữ cảnh cá nhân từ Notion** (Mục tiêu, Chấn thương) để đưa ra lời khuyên tập luyện hàng ngày qua Telegram.

## ✨ Tính năng nổi bật

* **⚡ On-Demand Trigger (Mới):**
    * Chat lệnh trực tiếp trên Telegram để kích hoạt phân tích ngay lập tức (`/daily`, `/sleep`, `/workout`).
    * Sử dụng **Cloudflare Workers** (Serverless) làm cầu nối, không cần treo máy tính 24/7.

* **🧠 Notion Database Integration:**
    * Quản lý danh sách người dùng, mật khẩu và trạng thái Active trực quan trên Notion.
    * **Cá nhân hóa theo thời gian thực:** Cập nhật "Mục tiêu" hoặc "Tình trạng chấn thương" trên Notion, AI sẽ tự động điều chỉnh giáo án ngay lập tức.

* **📊 Phân tích Dữ liệu Chuyên sâu:**
    * **Giấc ngủ:** Phân tích chi tiết 3 giai đoạn (Deep, Light, REM) và thời gian ngủ thực tế (trừ lúc tỉnh giấc).
    * **Training Readiness:** Tính điểm sẵn sàng dựa trên Pin cơ thể (Body Battery), Stress và Giấc ngủ.
    * **Acute Training Load (7 ngày):** Tính toán tải tập luyện dựa trên nhịp tim (TRIMP Banister).

* **🤖 AI Coach (Gemini 2.0 Flash):** * Đóng vai HLV chuyên nghiệp, đưa ra bài tập cụ thể (Pace, Thời gian) dựa trên thể trạng thực tế.
    * Tự động tạo **Voice Script** (Text-to-Speech) để gửi lời nhắn động viên bằng giọng nói.

* **📲 Telegram Bot:**
    * **Morning Report (7:30 AM):** Phân tích giấc ngủ và lời khuyên đầu ngày.
    * **Training Report (5:00 PM):** Gửi giáo án chi tiết và phân tích tải lượng vận động.

* **☁️ Tự động hóa 100%:** Chạy miễn phí trên GitHub Actions.

## 🛠️ Yêu cầu chuẩn bị

Để chạy dự án, bạn cần:

1.  **Tài khoản Garmin Connect:** Email và Mật khẩu.
2.  **Google Gemini API Key:** Lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/).
3.  **Telegram Bot:** Token và Chat ID (lấy từ @BotFather và @userinfobot).
4.  **Notion Integration:**
    * Tạo Database trên Notion.
    * Lấy `NOTION_TOKEN` và `NOTION_DATABASE_ID`.
5.  **Cloudflare Account (Free):** Để tạo Worker làm Webhook trigger (nếu dùng tính năng chat lệnh).

## 🗂️ Cấu trúc Database trên Notion

Bạn cần tạo một Database (Full page) trên Notion với các cột chính xác như sau để Code hoạt động:

| Tên Cột (Property)          | Loại (Type) | Mô tả                                                 |
| --------------------------- | ----------- | ----------------------------------------------------- |
| **Name** | Title       | Tên hiển thị của VĐV.                                 |
| **Email** | Email       | Email đăng nhập Garmin.                               |
| **Password** | Text        | Mật khẩu Garmin.                                      |
| **Telegram Chat ID** | Text        | ID chat Telegram (Dạng Text để tránh lỗi format số).  |
| **Training Goal** | Text        | VD: "Marathon Sub 4", "Chạy dưỡng sinh".              |
| **Chấn thương & Bệnh tật** | Text        | VD: "Đau gối phải", "Đang ốm".                        |
| **Ghi chú** | Text        | Ghi chú thêm cho AI.                                  |
| **Active** | Checkbox    | Tick ✅ để bật Bot cho user này.                        |

> **Lưu ý:** Sau khi tạo Database, hãy nhớ cấp quyền cho Bot truy cập bằng cách bấm vào `...` > `Connections` > `Connect to` > Chọn Integration của bạn.

## 🚀 Cài đặt & Chạy (Local)

1.  **Clone repository:**
    ```bash
    git clone [https://github.com/khoitran1999/garminbot.git](https://github.com/khoitran1999/garminbot.git)
    cd garminbot
    ```

2.  **Cài đặt thư viện:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Đảm bảo đã có `notion-client` và `garminconnect` bản mới nhất)*.

3.  **Cấu hình biến môi trường:**
    Tạo file `.env` với nội dung:
    ```env
    TELEGRAM_TOKEN="your_tele_token"
    GEMINI_API_KEY="your_gemini_key"
    NOTION_TOKEN="secret_your_notion_token"
    NOTION_DATABASE_ID="your_database_id"
    ```

4.  **Chạy thử nghiệm:**
    * Chạy Bot chính (Chế độ Daily): 
        ```bash
        python main.py --mode daily
        ```
    * Chạy Bot Sleep Analysis (Chế độ Sleep): 
        ```bash
        python main.py --mode sleep_analysis
        ```

## ⚙️ Triển khai trên GitHub Actions

Bạn không cần server riêng, Bot sẽ chạy tự động trên GitHub.

1.  **Fork** dự án này về GitHub của bạn.
2.  Vào **Settings** > **Secrets and variables** > **Actions**.
3.  Thêm các **Repository secrets** sau (Lấy giá trị từ file `.env` của bạn):
    * `TELEGRAM_TOKEN`
    * `GEMINI_API_KEY`
    * `NOTION_TOKEN`
    * `NOTION_DATABASE_ID`

4.  GitHub Actions sẽ tự động chạy theo lịch:
    * **Sleep Analysis:** 07:30 (Giờ VN).
    * **Daily Report:** 17:00 (Giờ VN).

---

## ⚡ Cấu hình Telegram Trigger (Cloudflare Workers)

Để chat với Bot và nhận kết quả ngay lập tức (thay vì chờ lịch chạy), hãy làm theo bước này:

### Bước 1: Tạo GitHub Workflow
Đảm bảo trong repo có file `.github/workflows/telegram_trigger.yml` để lắng nghe sự kiện `repository_dispatch`.

### Bước 2: Tạo Cloudflare Worker
1.  Đăng nhập Cloudflare > **Workers & Pages** > **Create Worker**.
2.  Vào **Edit Code** và dán code JavaScript xử lý Webhook (Code bridge gọi GitHub API).
3.  Vào **Settings** > **Variables and Secrets** > Thêm các biến:
    * `GITHUB_TOKEN`: Token GitHub (Classic) có quyền `repo` & `workflow`.
    * `TG_BOT_TOKEN`: Token Telegram Bot.
    * `ALLOWED_USER_ID`: ID Telegram của bạn (để bảo mật).
    * `GITHUB_OWNER` & `GITHUB_REPO`: Thông tin repo của bạn.

### Bước 3: Kết nối Webhook
Chạy đường dẫn sau trên trình duyệt để báo Telegram chuyển tin nhắn về Cloudflare: