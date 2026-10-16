import pytest
from backend.services.redis_service import redis_service
from backend.services.notion_service import get_user_by_email

def test_redis_garmin_tokens_methods():
    if not redis_service._client:
        pytest.skip("Redis not connected")

    test_email = "test_unit_opt@example.com"
    token_str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token"

    saved = redis_service.save_garmin_tokens(test_email, token_str, ttl_seconds=60)
    assert saved is True

    retrieved = redis_service.get_garmin_tokens(test_email)
    assert retrieved == token_str

    # Cleanup
    redis_service._client.delete(f"garmin_tokens:{test_email.lower()}")

def test_redis_user_cache_and_get_user_by_email():
    if not redis_service._client:
        pytest.skip("Redis not connected")

    test_email = "runner_test@example.com"
    user_data = {"name": "Test Runner", "email": test_email, "password": "pass", "goal": "Sub 3 Marathon"}

    saved = redis_service.set_user_cache(test_email, user_data, ttl_seconds=60)
    assert saved is True

    retrieved = redis_service.get_user_cache(test_email)
    assert retrieved is not None
    assert retrieved["name"] == "Test Runner"
    assert retrieved["email"] == test_email
    assert retrieved["goal"] == "Sub 3 Marathon"

    # Test get_user_by_email cache hit
    user_hit = get_user_by_email(test_email)
    assert user_hit is not None
    assert user_hit["name"] == "Test Runner"
    assert user_hit["email"] == test_email

    # Cleanup
    redis_service._client.delete(f"user_cache:{test_email.lower()}")

def test_redis_prompts_cache():
    if not redis_service._client:
        pytest.skip("Redis not connected")

    mock_prompts = {
        "daily_report": {"system_prompt": "You are a coach", "user_template": "Analyze {goal}", "model": "gemini-flash"}
    }
    saved = redis_service.set_prompts_cache(mock_prompts, ttl_seconds=60)
    assert saved is True

    cached = redis_service.get_prompts_cache()
    assert cached is not None
    assert "daily_report" in cached
    assert cached["daily_report"]["model"] == "gemini-flash"

    # Cleanup
    redis_service._client.delete("notion_prompts_cache")

def test_redis_chat_history():
    if not redis_service._client:
        pytest.skip("Redis not connected")

    test_user_id = "chat_user@example.com"
    # Clean previous
    redis_service._client.delete(f"chat_history:{test_user_id}")

    redis_service.save_chat_message(test_user_id, "user", "Xin chào AI Coach")
    redis_service.save_chat_message(test_user_id, "assistant", "Chào bạn, tôi có thể giúp gì?")

    history = redis_service.get_chat_history(test_user_id, limit=5)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Xin chào AI Coach"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Chào bạn, tôi có thể giúp gì?"

    # Cleanup
    redis_service._client.delete(f"chat_history:{test_user_id}")

def test_redis_dedup_and_ratelimit():
    if not redis_service._client:
        pytest.skip("Redis not connected")

    test_user = "dedup_user@example.com"
    date_str = "2026-10-16"
    mode = "daily_test"

    # Clean
    redis_service.delete_dedup(test_user, date_str, mode)
    redis_service._client.delete(f"ratelimit:{test_user}:{mode}")

    # First attempt should succeed
    is_new = redis_service.check_and_set_dedup(test_user, date_str, mode)
    assert is_new is True

    # Second attempt should be blocked
    is_duplicate = redis_service.check_and_set_dedup(test_user, date_str, mode)
    assert is_duplicate is False

    # Delete dedup
    deleted = redis_service.delete_dedup(test_user, date_str, mode)
    assert deleted is True

    # Rate limiting test
    assert redis_service.is_rate_limited(test_user, mode, limit=2, window_seconds=60) is False
    assert redis_service.is_rate_limited(test_user, mode, limit=2, window_seconds=60) is False
    assert redis_service.is_rate_limited(test_user, mode, limit=2, window_seconds=60) is True

    # Cleanup
    redis_service._client.delete(f"ratelimit:{test_user}:{mode}")
