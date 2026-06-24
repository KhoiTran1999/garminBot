import os
import httpx
from dotenv import load_dotenv

from app.config import Config

def get_users_from_notion():
    """
    Kết nối Notion, lấy danh sách user có trạng thái Active = True.
    Trả về list các dict user.
    """
    token = Config.NOTION_TOKEN
    database_id = Config.NOTION_DATABASE_ID

    if not token or not database_id:
        print("❌ Lỗi: Thiếu cấu hình NOTION_TOKEN hoặc NOTION_DATABASE_ID.")
        return []

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Filter: Chỉ lấy user có Active = true
    payload = {
        "filter": {
            "property": "Active",
            "checkbox": {
                "equals": True
            }
        }
    }

    print("Loading users from Notion...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"❌ Lỗi API Notion: {response.status_code} - {response.text}")
                return []

            data = response.json()
            results = data.get("results", [])
            users = []

            for page in results:
                props = page.get("properties", {})
                
                # Hàm helper lấy text an toàn
                def get_text(key, type_key="rich_text"):
                    if key not in props: return ""
                    try:
                        obj = props[key]
                        if type_key == "title":
                            return obj["title"][0]["plain_text"] if obj.get("title") else ""
                        elif type_key == "rich_text":
                            return obj["rich_text"][0]["plain_text"] if obj.get("rich_text") else ""
                        elif type_key == "email":
                            return obj.get("email", "")
                        elif type_key == "number": # Phòng hờ Chat ID để dạng số
                            return str(obj.get("number", ""))
                    except:
                        return ""

                # Mapping dữ liệu từ các cột Notion của bạn
                user = {
                    "name": get_text("Name", "title"),
                    "email": get_text("Email", "email"),
                    "password": get_text("Password", "rich_text"), # Cột Password của bạn là Text
                    "telegram_chat_id": get_text("Telegram Chat ID", "rich_text"), # Cột Chat ID là Text
                    
                    # Các trường bổ sung cho AI
                    "goal": get_text("Training Goal", "rich_text"),
                    "note": get_text("Ghi chú", "rich_text"),
                    
                    # Xử lý cột chấn thương (Ưu tiên tên chính xác, fallback tên ngắn)
                    "injury": get_text("Chấn thương & Bệnh tật", "rich_text") or get_text("Chấn thương", "rich_text") or "Không có"
                }

                # Chỉ thêm user nếu có đủ email/pass
                if user["email"] and user["password"]:
                    users.append(user)
            
            print(f"Found {len(users)} active users.")
            return users

    except Exception as e:
        print(f"Exception calling Notion: {e}")
        return []
