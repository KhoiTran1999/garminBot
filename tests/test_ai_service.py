import json
from datetime import datetime, timedelta
import pytz
from unittest.mock import MagicMock
from app.services.ai_service import execute_garmin_tool

def test_get_body_battery_trend_charging_periods():
    # Setup mock client
    client = MagicMock()

    # Generate some mock body battery readings representing charging and discharging
    # Timezone: Asia/Ho_Chi_Minh
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    base_time = vn_tz.localize(datetime(2026, 7, 7, 0, 0, 0))

    # We will construct a sequence:
    # 00:00 - 02:00: Sleep (charging from 10 to 60) -> 40 points (every 3 mins)
    # 02:00 - 04:00: Drop/awake (discharging from 60 to 50) -> 40 points
    # 04:00 - 06:00: Sleep again (charging from 50 to 90) -> 40 points
    # Let's verify our charging segment detector splits this into 2 charging periods:
    # 1. 00:00 to 02:00 (amount: 50, rate_per_hour = 25.0)
    # 2. 04:00 to 06:00 (amount: 40, rate_per_hour = 20.0)
    # The fastest should be 00:00 to 02:00

    bb_values = []

    # 00:00 to 02:00 (charging)
    for i in range(41): # 0 to 40 inclusive (40 * 3 = 120 mins)
        t = base_time + timedelta(minutes=i * 3)
        val = 10.0 + i * 1.25 # starts at 10.0, ends at 60.0
        bb_values.append([int(t.timestamp() * 1000), val])

    # 02:03 to 03:57 (discharging)
    # To trigger a segment end, the next value must be strictly smaller.
    for i in range(1, 40):
        t = base_time + timedelta(hours=2, minutes=i * 3)
        val = 60.0 - i * 0.3 # strictly decreasing (60.0 to 48.3)
        bb_values.append([int(t.timestamp() * 1000), val])

    # 04:00 to 06:00 (charging again)
    for i in range(41):
        t = base_time + timedelta(hours=4, minutes=i * 3)
        val = 40.0 + i * 1.25 # starts at 40.0, ends at 90.0
        bb_values.append([int(t.timestamp() * 1000), val])

    # Mock return values for client
    client.get_body_battery.return_value = [{
        "bodyBatteryValuesArray": bb_values,
        "charged": 90,
        "drained": 10
    }]
    client.get_body_battery_events.return_value = []

    # Call execute_garmin_tool
    args = {"date": "2026-07-07"}
    res_str = execute_garmin_tool(client, "get_body_battery_trend", args)

    res = json.loads(res_str)

    # Verify fastest charging period
    fastest = res.get("fastest_charging_period")
    assert fastest is not None
    assert fastest["start_time"] == "00:00"
    assert fastest["end_time"] == "02:00"
    assert fastest["charge_amount"] == 50.0
    assert fastest["duration_minutes"] == 120
    assert fastest["rate_per_hour"] == 25.0

    # Verify charging periods
    periods = res.get("charging_periods")
    assert len(periods) == 2

    assert periods[0]["start_time"] == "00:00"
    assert periods[0]["end_time"] == "02:00"
    assert periods[0]["charge_amount"] == 50.0
    assert periods[0]["rate_per_hour"] == 25.0

    assert periods[1]["start_time"] == "04:00"
    assert periods[1]["end_time"] == "06:00"
    assert periods[1]["charge_amount"] == 50.0
    assert periods[1]["rate_per_hour"] == 25.0
