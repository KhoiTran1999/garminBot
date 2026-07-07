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
            assert "Trích xuất các số liệu quan trọng nhất" in user_prompt
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
