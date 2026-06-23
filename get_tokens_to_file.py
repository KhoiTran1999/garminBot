import os
import json
from app.services.notion_service import get_users_from_notion
from garminconnect import Garmin

def main():
    users = get_users_from_notion()
    results = []
    
    for user in users:
        email = user.get('email')
        password = user.get('password')
        name = user.get('name')
        
        if not email or not password:
            continue
            
        try:
            client = Garmin(email, password)
            client.login()
            token_str = client.garth.dumps()
            
            env_var_name = f"GARMINTOKENS_{email.replace('@', '_').replace('.', '_').upper()}"
            results.append({
                "name": name,
                "email": email,
                "github_secret_name": env_var_name,
                "github_secret_value": token_str
            })
            print(f"✅ Đã lấy token cho {name}")
        except Exception as e:
            print(f"❌ Lỗi {email}: {e}")

    with open("garmin_tokens.txt", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"Tài khoản: {r['name']} ({r['email']})\n")
            f.write(f"Secret Name: {r['github_secret_name']}\n")
            f.write(f"Secret Value:\n{r['github_secret_value']}\n")
            f.write("="*80 + "\n\n")
            
    print("\n✅ Đã lưu tất cả token vào file: garmin_tokens.txt")

if __name__ == "__main__":
    main()
