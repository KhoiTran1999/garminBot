import datetime
from garminconnect import Garmin
import json
import os

try:
    with open('garmin_tokens.txt', 'r') as f:
        tokens = json.load(f)
    client = Garmin(email='', password='')
    client.login(tokens.get('oauth_token'), tokens.get('oauth_token_secret'))
    today = datetime.date.today().isoformat()
    hrv = client.get_hrv_data(today)
    ts = client.get_training_status(today)
    print("HRV Keys:", hrv.keys() if hrv else "None")
    print("TS Keys:", ts.keys() if ts else "None")
except Exception as e:
    print(f"Error: {e}")
