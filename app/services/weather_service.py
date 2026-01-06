import requests
from typing import Dict, Any, Optional

WAQI_API_URL = "https://api.waqi.info/feed/A476167/?token=70adc343f004e025d9387640a136716cd4a1c0f2"

class WeatherService:
    @staticmethod
    def get_aqi_data() -> Optional[Dict[str, Any]]:
        """
        Fetches AQI and PM2.5 data from the WAQI API.
        Returns a dictionary with 'aqi' and 'pm25' if successful, else None.
        """
        try:
            response = requests.get(WAQI_API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "ok":
                iaqi = data.get("data", {}).get("iaqi", {})
                pm25 = iaqi.get("pm25", {}).get("v", "N/A")
                aqi = data.get("data", {}).get("aqi", "N/A")
                city_name = data.get("data", {}).get("city", {}).get("name", "Unknown Location")
                
                print(f"✅ WeatherService: Fetched AQI ({aqi}), PM2.5 ({pm25}) for {city_name}.")
                
                return {
                    "aqi": aqi,
                    "pm25": pm25,
                    "city": city_name
                }
            else:
                print(f"⚠️ WeatherService: API returned status '{data.get('status')}'.")
                return None
        except Exception as e:
            print(f"❌ WeatherService: Error fetching data - {e}")
            return None
