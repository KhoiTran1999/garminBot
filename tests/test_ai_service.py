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
