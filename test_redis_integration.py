import os
import asyncio
from datetime import date
from app.services.redis_service import redis_service
from app.services.ai_service import get_ai_advice
from app.config import Config

async def test_all():
    print("=== START TESTING REDIS INTEGRATION ===")

    # Check client existence
    print("Redis client initialized:", bool(redis_service._client))
    if not redis_service._client:
        print("❌ Redis not connected!")
        return

    # Clear prior keys if any, so test is clean
    test_tele_id = "123456789_test"
    test_email = "test@example.com"
    test_mode = "daily"
    today_str = date.today().isoformat()

    redis_service._client.delete(f"sent:{test_tele_id}:{test_mode}")
    redis_service._client.delete(f"ratelimit:{test_tele_id}:{test_mode}")
    redis_service._client.delete(f"ai_context:{test_email}:{test_mode}")

    # 1. Test Deduplication Lock
    print("\n--- 1. Testing Deduplication Lock ---")
    r1 = redis_service.check_and_set_dedup(test_tele_id, today_str, test_mode)
    print("First check (should be True):", r1)
    r2 = redis_service.check_and_set_dedup(test_tele_id, today_str, test_mode)
    print("Second check (should be False):", r2)

    # Test release
    redis_service.delete_dedup(test_tele_id, today_str, test_mode)
    r3 = redis_service.check_and_set_dedup(test_tele_id, today_str, test_mode)
    print("Check after release (should be True):", r3)

    # 2. Test Rate Limiter (Limit: 3 per 10 mins)
    print("\n--- 2. Testing Rate Limiter ---")
    for i in range(1, 6):
        limited = redis_service.is_rate_limited(test_tele_id, test_mode, limit=3, window_seconds=10)
        print(f"Trigger {i}: is_rate_limited =", limited)

    # 3. Test AI Context
    print("\n--- 3. Testing AI Context ---")
    redis_service.save_ai_context(test_email, test_mode, "Report day 1", limit=3)
    redis_service.save_ai_context(test_email, test_mode, "Report day 2", limit=3)
    redis_service.save_ai_context(test_email, test_mode, "Report day 3", limit=3)
    redis_service.save_ai_context(test_email, test_mode, "Report day 4", limit=3)

    reports = redis_service.get_ai_context(test_email, test_mode, limit=3)
    print("Latest 3 reports (should only be days 4, 3, 2):", reports)

    # 4. Test Chat History
    print("\n--- 4. Testing Chat History ---")
    redis_service.save_chat_message(test_tele_id, "user", "Hello", limit=5)
    redis_service.save_chat_message(test_tele_id, "assistant", "Hi there!", limit=5)
    redis_service.save_chat_message(test_tele_id, "user", "How are you?", limit=5)

    history = redis_service.get_chat_history(test_tele_id, limit=5)
    print("Chat history (should be user Hello, assistant Hi there, user How are you):", history)

    # Cleanup test keys
    redis_service._client.delete(f"sent:{test_tele_id}:{test_mode}")
    redis_service._client.delete(f"ratelimit:{test_tele_id}:{test_mode}")
    redis_service._client.delete(f"ai_context:{test_email}:{test_mode}")
    redis_service._client.delete(f"chat_history:{test_tele_id}")
    print("\n=== TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(test_all())
