import os
import json
from datetime import date, timedelta
from garminconnect import Garmin
from dotenv import load_dotenv

# --- CẤU HÌNH ---
load_dotenv()

# Bạn có thể điền trực tiếp email/pass vào đây nếu không dùng .env
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL") or "tranquockhoi1999@gmail.com"
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD") or "@Khoitran990120"

def pretty_print(title, data):
    print(f"\n--- {title} ---")
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Không có dữ liệu hoặc lỗi.")

def main():
    if not GARMIN_EMAIL or "YOUR_EMAIL_HERE" in GARMIN_EMAIL:
        print("❌ Vui lòng điền GARMIN_EMAIL và GARMIN_PASSWORD vào file hoặc .env")
        return

    print(f"🔄 Đang đăng nhập Garmin với email: {GARMIN_EMAIL}...")
    try:
        client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        client.login()
        print("✅ Đăng nhập thành công!")
    except Exception as e:
        print(f"❌ Lỗi đăng nhập: {e}")
        return

    today = date.today()
    # Lấy 24h qua: Hôm nay và hôm qua
    start_date = today - timedelta(days=1)
    
    today_str = today.isoformat()
    start_date_str = start_date.isoformat()
    
    print(f"📅 Đang lấy dữ liệu từ {start_date_str} đến {today_str} (24h qua)...")

    all_results = {"date": today_str}

    # 1. Progress Summary Between Dates
    try:
        progress = client.get_progress_summary_between_dates(start_date_str, today_str)
        # pretty_print(f"Progress Summary ({start_date_str} - {today_str})", progress)
        print("✅ Đã lấy Progress Summary")
        all_results["get_progress_summary_between_dates"] = progress
    except Exception as e:
        print(f"⚠️ Lỗi get_progress_summary_between_dates: {e}")
        all_results["get_progress_summary_between_dates"] = {"error": str(e)}

    # 2. Deep Analysis: Activities in last 24h
    try:
        print(f"\n🔄 Đang lấy danh sách hoạt động...")
        # Lấy tất cả loại hoạt động (type="")
        activities = client.get_activities_by_date(start_date_str, today_str, "")
        
        all_results["activities_analysis"] = []

        if activities:
            print(f"✅ Tìm thấy {len(activities)} hoạt động.")
            
            for activity in activities:
                activity_id = activity.get("activityId")
                activity_name = activity.get("activityName")
                print(f"\n🔍 Đang phân tích hoạt động: {activity_name} (ID: {activity_id})")
                
                activity_details = {
                    "activityId": activity_id,
                    "activityName": activity_name,
                    "summary": activity
                }

                # a. Activity Splits
                try:
                    splits = client.get_activity_splits(activity_id)
                    activity_details["splits"] = splits
                except Exception as e:
                     print(f"⚠️ Lỗi get_activity_splits: {e}")
                     activity_details["splits"] = {"error": str(e)}

                # b. Weather
                try:
                    weather = client.get_activity_weather(activity_id)
                    activity_details["weather"] = weather
                except Exception as e:
                     print(f"⚠️ Lỗi get_activity_weather: {e}")
                     activity_details["weather"] = {"error": str(e)}

                # c. HR Zones
                try:
                    hr_zones = client.get_activity_hr_in_timezones(activity_id)
                    activity_details["hr_zones"] = hr_zones
                except Exception as e:
                     print(f"⚠️ Lỗi get_activity_hr_in_timezones: {e}")
                     activity_details["hr_zones"] = {"error": str(e)}

                # d. Power Zones
                try:
                    power_zones = client.get_activity_power_in_timezones(activity_id)
                    activity_details["power_zones"] = power_zones
                except Exception as e:
                     # print(f"⚠️ Lỗi get_activity_power_in_timezones: {e}")
                     pass

                # e. Activity Details
                try:
                    details = client.get_activity_details(activity_id)
                    print(f"   ✅ Đã lấy chi tiết (details)")
                    activity_details["activity_details"] = details
                except Exception as e:
                     print(f"⚠️ Lỗi get_activity_details: {e}")
                     activity_details["activity_details"] = {"error": str(e)}
                
                all_results["activities_analysis"].append(activity_details)

        else:
            print("⚠️ Không tìm thấy hoạt động nào trong khoảng thời gian này.")
            all_results["activities_analysis"] = "No activity found"
            
    except Exception as e:
        print(f"⚠️ Lỗi lấy danh sách Activity: {e}")
        all_results["activities_analysis"] = {"error": str(e)}

    # Save to JSON file
    output_file = "garmin_data_output.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Đã lưu toàn bộ kết quả vào file: {output_file}")
    except Exception as e:
        print(f"\n❌ Lỗi khi lưu file JSON: {e}")

if __name__ == "__main__":
    main()
