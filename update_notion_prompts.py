import httpx
import json
from app.config import Config

token = Config.NOTION_TOKEN
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def update_page(page_id, updates):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    with httpx.Client(timeout=15.0) as client:
        resp = client.patch(url, headers=headers, json={"properties": updates})
        if resp.status_code == 200:
            print(f"  ✅ Updated {page_id}")
        else:
            print(f"  ❌ Error {resp.status_code}: {resp.text}")

def rich_text_block(text):
    """Split text into 2000-char chunks for Notion rich_text limit"""
    chunks = []
    while text:
        chunks.append({"type": "text", "text": {"content": text[:2000]}})
        text = text[2000:]
    return chunks

# ============================================================
# FIX 1: Rename the fake "daily_report" (Productivity Coach) -> "task_planner"
# ============================================================
print("1. Renaming Productivity Coach prompt -> task_planner")
update_page("2ded7e63-5304-8003-b05f-e1db90a0c71f", {
    "Name": {
        "title": [{"type": "text", "text": {"content": "task_planner"}}]
    }
})

# ============================================================
# FIX 2: Fix daily_report (real) - clean name + add Readiness guide
# ============================================================
print("\n2. Fixing daily_report: clean name + add Readiness guide to system prompt")

daily_system = """Bạn là Huấn luyện viên thể thao chuyên nghiệp (AI Running Coach).
Hãy phân tích dữ liệu và đưa ra giáo án cho VĐV.

📏 THANG ĐIỂM SẴN SÀNG (Readiness Score):
• 85-100: Sung sức — Có thể tập cường độ cao, interval, race pace
• 70-84: Khá tốt — Tập bình thường, tempo run, strength training
• 50-69: Trung bình — Nên tập nhẹ, easy run, recovery, yoga
• 30-49: Mệt mỏi — Nghỉ ngơi hoặc chỉ đi bộ/stretching
• Dưới 30: Kiệt sức — Bắt buộc nghỉ, ưu tiên phục hồi

YÊU CẦU OUTPUT (Markdown Telegram):
Trả về báo cáo theo format dưới đây, văn phong thân thiện nhưng chuyên môn:
🔢 TỔNG QUAN HÔM NAY
[Tổng hợp các chỉ số hiện tại của cơ thể và giấc ngủ và chất lượng không khí.]
🔥 ĐÁNH GIÁ TRẠNG THÁI
[Cơ thể đang Sung sức hay Mệt mỏi? Giấc ngủ và Stress ảnh hưởng thế nào?]
🏃 BÀI TẬP ĐỀ XUẤT
[Dựa trên điểm Sẵn sàng và Tải tập luyện, đề xuất có nên tập hay nghỉ ngơi. Nếu tập, gợi ý cường độ và loại bài tập phù hợp.]
💡 LỜI KHUYÊN
[Một lời khuyên về dinh dưỡng hoặc phục hồi phù hợp với goal hiện tại.]
LƯU Ý: Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách."""

daily_user = """Dữ liệu đầu vào:
Thông tin VĐV: {user_label}.
Thời gian báo cáo hiện tại: {current_now}
THÔNG TIN MÔI TRƯỜNG:
{aqi_info}
HỒ SƠ VĐV:
- Mục tiêu hiện tại: {goal}
- Tình trạng chấn thương/Bệnh lý: {injury}
- Ghi chú thêm: {note}
DỮ LIỆU CƠ THỂ HÔM NAY:
- Điểm Sẵn sàng: {r_score}/100
- Cơ thể: Pin Body Battery {r_data[body_battery]}/100 | Stress {r_data[stress]} (Thấp <25, Cao >50)
- Giấc ngủ: {r_data[sleep_text]}
{nap_text}
- Nhịp tim nghỉ (RHR): {r_data[rhr]} bpm
- SpO2: {spo2_text}
- Hô hấp: {resp_text}
TẢI TẬP LUYỆN (7 NGÀY):
- Tải trung bình ngày (Acute Load): {avg_daily_load_int} (TRIMP Index)
- Lịch sử hoạt động:
{activities_text}"""

update_page("2ded7e63-5304-8024-be40-fc056b360378", {
    "Name": {
        "title": [{"type": "text", "text": {"content": "daily_report"}}]
    },
    "System Prompt": {
        "rich_text": rich_text_block(daily_system)
    },
    "User Template": {
        "rich_text": rich_text_block(daily_user)
    }
})

# ============================================================
# FIX 3: Fix sleep_analysis - clean name + add Readiness guide + Nap
# ============================================================
print("\n3. Fixing sleep_analysis: clean name + add Readiness guide + Nap info")

sleep_system = """Bạn là Chuyên gia giấc ngủ và Hiệu suất thể thao (AI Sleep Coach).
Hãy phân tích dữ liệu giấc ngủ đêm qua dựa trên các tiêu chuẩn của Hiệp hội Giấc ngủ Quốc gia (National Sleep Foundation) để đảm bảo tính khoa học và đưa ra lời khuyên đầu ngày cho VĐV:

📏 THANG ĐIỂM SẴN SÀNG (Readiness Score):
• 85-100: Phục hồi xuất sắc — Sẵn sàng cho ngày mới với năng lượng cao
• 70-84: Phục hồi tốt — Cơ thể ổn, có thể hoạt động bình thường
• 50-69: Phục hồi trung bình — Cần chú ý nghỉ ngơi thêm trong ngày
• 30-49: Phục hồi kém — Nên ưu tiên nghỉ ngơi, tránh gắng sức
• Dưới 30: Chưa phục hồi — Cần nghỉ ngơi hoàn toàn, kiểm tra sức khỏe

YÊU CẦU OUTPUT (Markdown Telegram): Trả về báo cáo ngắn gọn, tập trung vào chất lượng giấc ngủ và sự sẵn sàng cho ngày mới:
**💤 PHÂN TÍCH GIẤC NGỦ**
[Dựa vào các chỉ số trên để phân tích giấc ngủ]
**🔋 TRẠNG THÁI PHỤC HỒI**
[Dựa trên Body Battery và Stress, cơ thể đã nạp đủ năng lượng chưa?]
**🌅 LỜI KHUYÊN SÁNG NAY**
[Đề xuất cải thiện giấc ngủ và lời khuyên để có một ngày tốt lành.]
LƯU Ý: Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách."""

sleep_user = """Dữ liệu đầu vào:
Thông tin VĐV: {user_label}.         Thời gian báo cáo hiện tại: {current_now}
THÔNG TIN MÔI TRƯỜNG:
{aqi_info}
HỒ SƠ VĐV:
- Mục tiêu: {goal}
- Chấn thương: {injury}        - Lưu ý: {note}

DỮ LIỆU ĐÊM QUA & SÁNG NAY:
- Điểm Sẵn sàng (Readiness): {r_score}/100
- Giấc ngủ: {r_data[sleep_text]} (Ngủ nông/sâu/REM)
{nap_text}
- Phục hồi: Body Battery {r_data[body_battery]}/100 | Stress {r_data[stress]}
- Nhịp tim nghỉ (RHR): {r_data[rhr]} bpm
- SpO2 (Oxy máu): {spo2_text}
- Hô hấp (Respiration): {resp_text}"""

update_page("2ded7e63-5304-8022-a42a-c7ccd7f2edf0", {
    "Name": {
        "title": [{"type": "text", "text": {"content": "sleep_analysis"}}]
    },
    "System Prompt": {
        "rich_text": rich_text_block(sleep_system)
    },
    "User Template": {
        "rich_text": rich_text_block(sleep_user)
    }
})

# ============================================================
# FIX 4: Fix workout_analysis - clean name (remove \n\n)
# ============================================================
print("\n4. Fixing workout_analysis: clean name")
update_page("2ded7e63-5304-8009-bdf1-c9e242e21bd6", {
    "Name": {
        "title": [{"type": "text", "text": {"content": "workout_analysis"}}]
    }
})

print("\n=== DONE ===")
