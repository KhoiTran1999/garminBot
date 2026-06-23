import os
import getpass
from garminconnect import Garmin

def main():
    print("=== TOOL LẤY GARMIN TOKEN CHO GITHUB ACTIONS ===")
    email = input("Nhập Email Garmin: ").strip()
    password = getpass.getpass("Nhập Mật khẩu Garmin (gõ không hiện chữ): ").strip()
    
    try:
        client = Garmin(email, password)
        client.login()
        token_str = client.garth.dumps()
        
        env_var_name = f"GARMINTOKENS_{email.replace('@', '_').replace('.', '_').upper()}"
        print("\n✅ Lấy token thành công! Bấm bôi đen hoặc Ctrl+C để copy toàn bộ chuỗi ký tự bên dưới:\n")
        print("-" * 50)
        print(token_str)
        print("-" * 50)
        
        print(f"\n👉 HƯỚNG DẪN THÊM VÀO GITHUB:")
        print("1. Vào Repository trên GitHub -> Settings -> Secrets and variables -> Actions")
        print("2. Bấm 'New repository secret'")
        print(f"3. Name: GARMINTOKENS")
        print("4. Secret: <Paste nguyên chuỗi ký tự gạch đứt bên trên vào>")
        print("5. Bấm 'Add secret'")
        print("\nSau đó, trình chạy của Github Actions sẽ không bao giờ bị báo lỗi Too Many Requests / 429 nữa!")
        
    except Exception as e:
        print(f"❌ Đăng nhập thất bại (Có thể máy tính hiện tại cũng đang bị hạn chế IP, hãy chờ vài phút/bật VPN hoặc kiểm tra lại pass): {e}")

if __name__ == "__main__":
    main()
