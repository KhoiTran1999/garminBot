import json
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from app.services.ai_service import process_data_with_worker, execute_garmin_tool

@pytest.mark.asyncio
async def test_process_data_with_worker_with_task():
    # Mock call_ai_api_raw_async
    with patch("app.services.ai_service.call_ai_api_raw_async", new_callable=AsyncMock) as mock_call:
        mock_response = MagicMock()
        mock_response.content = "processed result by AI"
        mock_call.return_value = mock_response

        tool_args = {"date": "2026-07-07", "task": "Hãy lấy khoảng thời gian Body battery tăng nhanh nhất"}

        with patch("app.services.ai_service.Config") as mock_cfg:
            mock_cfg.ROUTER9_API_KEY = "fake-key"
            mock_cfg.MODEL_WORKER = "gemini-worker"

            res = await process_data_with_worker("get_body_battery_trend", tool_args, '{"charged": 10}')

            assert res == "processed result by AI"
            mock_call.assert_called_once()

            # Check prompt contents
            args, kwargs = mock_call.call_args
            messages = kwargs.get("messages") or args[2]
            user_prompt = messages[1]["content"]
            assert "Nhiệm vụ cụ thể của bạn được yêu cầu từ MODEL_BRAIN:" in user_prompt
            assert "Hãy lấy khoảng thời gian Body battery tăng nhanh nhất" in user_prompt

@pytest.mark.asyncio
async def test_process_data_with_worker_without_task():
    # Mock call_ai_api_raw_async
    with patch("app.services.ai_service.call_ai_api_raw_async", new_callable=AsyncMock) as mock_call:
        mock_response = MagicMock()
        mock_response.content = "processed result by AI"
        mock_call.return_value = mock_response

        tool_args = {"date": "2026-07-07"}

        with patch("app.services.ai_service.Config") as mock_cfg:
            mock_cfg.ROUTER9_API_KEY = "fake-key"
            mock_cfg.MODEL_WORKER = "gemini-worker"

            res = await process_data_with_worker("get_body_battery_trend", tool_args, '{"charged": 10}')

            assert res == "processed result by AI"

            # Check prompt contents
            args, kwargs = mock_call.call_args
            messages = kwargs.get("messages") or args[2]
            user_prompt = messages[1]["content"]
            assert "Trích xuất tất cả các số liệu quan trọng nhất" in user_prompt
            assert "Nhiệm vụ cụ thể của bạn được yêu cầu từ MODEL_BRAIN" not in user_prompt

def test_execute_garmin_tool_get_body_battery_trend():
    client = MagicMock()

    # Mock client output
    client.get_body_battery.return_value = [{
        "bodyBatteryValuesArray": [[1783357200000, 50]],
        "charged": 40,
        "drained": 20
    }]
    client.get_body_battery_events.return_value = [
        {"eventType": "NAP", "durationInMilliseconds": 1800000, "startTimeLocal": "2026-07-07T12:00:00"}
    ]

    args = {"date": "2026-07-07"}
    res_str = execute_garmin_tool(client, "get_body_battery_trend", args)

    res = json.loads(res_str)
    assert res["charged"] == 40
    assert res["drained"] == 20
    assert len(res["naps"]) == 1
    assert res["naps"][0]["duration_minutes"] == 30
    assert "body_battery_readings" in res
    assert "fastest_charging_period" not in res  # Verifies we reverted Python calculation

@patch("app.services.ai_service.call_ai_api")
@patch("app.services.ai_service.redis_service")
@patch("app.services.ai_service.Config")
def test_get_ai_advice_user_note(mock_cfg, mock_redis, mock_call):
    mock_cfg.ROUTER9_API_KEY = "fake-key"
    mock_cfg.MODEL_WORKER = "fake-model"
    mock_redis.get_ai_context.return_value = []

    from app.services.ai_service import get_ai_advice

    user_config = {"name": "Test User", "email": "test@test.com", "goal": "Running", "injury": "None", "note": "None"}
    r_data = {"nap_seconds": 0, "avg_spo2": 98, "min_spo2": 95, "last_spo2": 97,
              "avg_waking_resp": 12, "avg_sleep_resp": 14, "min_resp": 10, "max_resp": 18,
              "rhr": 60, "body_battery": 80, "stress": 20, "sleep_text": "Good", "timeseries_text": ""}

    # 1. Notion template WITHOUT {user_note} - should automatically append the note
    template_without = {"system_prompt": "Sys", "user_template": "Goal: {goal}", "model": "fake-model"}
    get_ai_advice(
        today="2026-07-07",
        r_data=r_data,
        r_score=85,
        l_data={"raw_activities_for_ai": []},
        user_config=user_config,
        prompt_template=template_without,
        mode="daily",
        user_note=" thức tới 2h sáng "
    )

    # Check what prompt was sent to call_ai_api
    args, kwargs = mock_call.call_args
    prompt_sent = args[2]
    assert "thức tới 2h sáng" in prompt_sent
    assert "- **Ghi chú hôm nay từ người dùng:** thức tới 2h sáng" in prompt_sent

    # 2. Notion template WITH {user_note} - should format it directly without duplication
    template_with = {"system_prompt": "Sys", "user_template": "Goal: {goal}. Note: {user_note}", "model": "fake-model"}
    mock_call.reset_mock()
    get_ai_advice(
        today="2026-07-07",
        r_data=r_data,
        r_score=85,
        l_data={"raw_activities_for_ai": []},
        user_config=user_config,
        prompt_template=template_with,
        mode="daily",
        user_note=" thức tới 2h sáng "
    )
    args, kwargs = mock_call.call_args
    prompt_sent = args[2]
    assert "Note: thức tới 2h sáng" in prompt_sent
    # verify that the automatic append logic did NOT trigger since it was already in template
    assert "- **Ghi chú hôm nay từ người dùng:** thức tới 2h sáng" not in prompt_sent

    # 3. Fallback/hardcoded templates
    mock_call.reset_mock()
    get_ai_advice(
        today="2026-07-07",
        r_data=r_data,
        r_score=85,
        l_data={"raw_activities_for_ai": []},
        user_config=user_config,
        prompt_template=None,
        mode="sleep_analysis",
        user_note=" thức tới 2h sáng "
    )
    args, kwargs = mock_call.call_args
    prompt_sent = args[2]
    assert "Ghi chú hôm nay từ người dùng:** thức tới 2h sáng" in prompt_sent

@patch("app.services.ai_service.call_ai_api")
@patch("app.services.ai_service.redis_service")
@patch("app.services.ai_service.Config")
def test_get_workout_and_battery_user_note(mock_cfg, mock_redis, mock_call):
    mock_cfg.ROUTER9_API_KEY = "fake-key"
    mock_cfg.MODEL_WORKER = "fake-model"
    mock_redis.get_ai_context.return_value = []

    from app.services.ai_service import get_workout_analysis_advice, get_battery_analysis_advice

    user_config = {"name": "Test User", "email": "test@test.com", "goal": "Running"}

    # Test workout analysis
    get_workout_analysis_advice(
        activity_data_list=[{"activityId": 123}],
        user_config=user_config,
        prompt_template=None,
        user_note=" chạy mệt quá "
    )
    args, kwargs = mock_call.call_args
    prompt_sent = args[2]
    assert "GHI CHÚ HÔM NAY TỪ NGƯỜI DÙNG: chạy mệt quá" in prompt_sent

    # Test battery analysis
    get_battery_analysis_advice(
        today="2026-07-07",
        r_data={"body_battery": 50, "stress": 30},
        user_config=user_config,
        prompt_template=None,
        user_note=" căng thẳng cả ngày "
    )
    args, kwargs = mock_call.call_args
    prompt_sent = args[2]
    assert "GHI CHÚ HÔM NAY TỪ NGƯỜI DÙNG: căng thẳng cả ngày" in prompt_sent


def test_execute_garmin_tool_get_custom_training_readiness():
    from datetime import datetime
    client = MagicMock()

    # Mock get_processed_data to return custom readiness data
    mock_r_data = {
        "sleep_hours": 7.2,
        "sleep_text": "Tổng ngủ thực: 7h 12p\n- Ngủ sâu: 1h\n- Ngủ nông: 5h\n- Ngủ mơ: 1h 12p\n- Thức: 0p",
        "stress": 25,
        "body_battery": 60,
        "hrv_status": "BALANCED",
        "rhr": 55,
        "avg_spo2": 96,
        "avg_sleep_resp": 14,
        "nap_seconds": 1200
    }
    mock_r_score = 82
    mock_l_data = {
        "avg_daily_load": 150
    }

    with patch("app.services.garmin_service.get_processed_data", return_value=(mock_r_data, mock_r_score, mock_l_data)) as mock_gpd:
        args = {"date": "2026-07-08"}
        res_str = execute_garmin_tool(client, "get_custom_training_readiness", args, user_label="Test User")

        res = json.loads(res_str)
        assert res["score"] == 82
        assert "Good" in res["assessment"]
        assert res["sleep_hours"] == 7.2
        assert res["stress_average"] == 25
        assert res["body_battery"] == 60
        assert res["hrv_status"] == "BALANCED"
        assert res["resting_heart_rate"] == 55
        assert res["avg_spo2"] == 96
        assert res["avg_sleep_resp"] == 14
        assert res["nap_duration_minutes"] == 20
        assert res["seven_day_acute_load"] == 150

        # We assert the date compared is a date object
        called_args, called_kwargs = mock_gpd.call_args
        assert called_args[0] == client
        assert called_args[1].year == 2026
        assert called_args[1].month == 7
        assert called_args[1].day == 8
        assert called_args[2] == "Test User"


def test_execute_garmin_tool_get_training_readiness_fallback():
    client = MagicMock()
    # Mock native client call to return None / raise exception, or return dict with None score Value
    client.get_training_readiness.return_value = {
        "trainingReadinessMap": {
            "scoreValue": None
        }
    }

    mock_r_data = {
        "sleep_hours": 8.0,
        "stress": 20,
        "body_battery": 80,
        "hrv_status": "BALANCED",
        "rhr": 50,
        "recovery_time_hours": 12
    }
    mock_r_score = 95
    mock_l_data = {}

    with patch("app.services.garmin_service.get_processed_data", return_value=(mock_r_data, mock_r_score, mock_l_data)) as mock_gpd:
        args = {"date": "2026-07-08"}
        res_str = execute_garmin_tool(client, "get_training_readiness", args, user_label="Test User")

        res = json.loads(res_str)
        assert res["score"] == 95
        assert res["assessment"] == "Prime"
        assert res["is_custom_calculated"] is True
        assert res["recovery_time_hours"] == 12
        assert res["sleep_history_score"] == 8.0
        assert res["hrv_status"] == "BALANCED"
        assert res["stress_history_score"] == 20

        mock_gpd.assert_called_once()

