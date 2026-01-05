
import asyncio
import os
from unittest.mock import MagicMock, patch
from app.services.telegram_service import send_error_alert
from app.config import Config

async def test_alert():
    print("--- TESTING SEND_ERROR_ALERT ---")
    
    # 1. Test with missing credentials (should print warning)
    print("\n[Test 1] Missing Credentials:")
    await send_error_alert(None, None, "Test Error")

    # 2. Test with Mocked Bot (Happy Path)
    print("\n[Test 2] Mocked Bot Success:")
    
    # Mock Token and Admin ID
    mock_token = "TEST_TOKEN"
    mock_admin_id = "123456"
    
    # Mock telegram.Bot
    with patch('app.services.telegram_service.Bot') as MockBot:
        mock_bot_instance = MockBot.return_value
        # Mock send_message to be an async function
        f = asyncio.Future()
        f.set_result(True)
        mock_bot_instance.send_message.return_value = f
        
        await send_error_alert(mock_token, mock_admin_id, "Test Error Message")
        
        # Verify call
        mock_bot_instance.send_message.assert_called_once()
        args, kwargs = mock_bot_instance.send_message.call_args
        print(f"Called with chat_id={kwargs['chat_id']}")
        print("✅ Correctly called Bot.send_message")

if __name__ == "__main__":
    asyncio.run(test_alert())
