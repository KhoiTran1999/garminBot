import os
import asyncio
from app.services.notion_service import get_users_from_notion
from garminconnect import Garmin

def main():
    users = get_users_from_notion()
    for user in users:
        email = user.get('email')
        password = user.get('password')
        name = user.get('name')
        
        if not email or not password:
            print(f"Skipping {name} - missing credentials")
            continue
            
        print(f"\n--- Lấy token cho {name} ({email}) ---")
        try:
            client = Garmin(email, password)
            client.login()
            token_str = client.garth.dumps()
            
            env_var_name = f"GARMINTOKENS_{email.replace('@', '_').replace('.', '_').upper()}"
            print(f"✅ Tên biến (Key) trên GitHub Secret: {env_var_name}")
            print("Value (Copy nội dung này):")
            print(token_str)
            print("-" * 50)
        except Exception as e:
            print(f"❌ Đăng nhập thất bại cho {email}: {e}")

if __name__ == "__main__":
    main()
