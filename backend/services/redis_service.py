import redis
import logging
from backend.config import Config

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_url = Config.REDIS_URL
        self._client = None
        self._connection_failed = False
        if not self.redis_url:
            logger.warning("⚠️ REDIS_URL not configured. Redis service will be bypassed (fail-safe).")
            self._connection_failed = True
        else:
            try:
                # Initialize Redis client. Use socket_timeout to fail fast.
                self._client = redis.Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0
                )
                # Test connection
                self._client.ping()
                logger.info("✅ Redis connected successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis at {self.redis_url}: {e}")
                self._client = None
                self._connection_failed = True

    def _execute(self, func, default_return, *args, **kwargs):
        """
        Helper method to execute a Redis command with fail-safe behavior.
        """
        if self._connection_failed or not self._client:
            return default_return

        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"⚠️ Redis command failed: {e}. Bypassing Redis.")
            # Mark connection failed temporarily so subsequent requests don't hang
            return default_return

    def check_and_set_dedup(self, user_id: str, date_str: str, mode: str) -> bool:
        """
        Check if a report has already been sent for the user on the given date and mode.
        Allows up to 2 times a day by enforcing a 12-hour gap (43200 seconds).
        Returns:
            True if it's a new report (successfully set deduplication lock).
            False if it has already been sent (deduplication lock exists) or if Redis fails.
        """
        if not user_id:
            return True

        key = f"sent:{user_id}:{mode}"

        def _op():
            return bool(self._client.set(key, "1", ex=3600, nx=True))

        return self._execute(_op, default_return=True)

    def delete_dedup(self, user_id: str, date_str: str, mode: str) -> bool:
        """
        Delete a deduplication lock if a run failed.
        """
        if not user_id:
            return True

        key = f"sent:{user_id}:{mode}"

        def _op():
            return bool(self._client.delete(key))

        return self._execute(_op, default_return=True)

    def is_rate_limited(self, user_id: str, mode: str, limit: int = 3, window_seconds: int = 600) -> bool:
        """
        Rate limiter to prevent spamming triggers.
        Returns:
            True if the user is rate limited (exceeded threshold).
            False if the trigger is allowed.
        """
        if not user_id:
            return False

        key = f"ratelimit:{user_id}:{mode}"

        def _op():
            count_str = self._client.get(key)
            if count_str is not None:
                count = int(count_str)
                if count >= limit:
                    return True

            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results = pipe.execute()

            new_val = results[0]
            ttl = results[1]

            if new_val == 1 or ttl < 0:
                self._client.expire(key, window_seconds)

            return False

        return self._execute(_op, default_return=False)

    def get_ai_context(self, email: str, mode: str, limit: int = 3) -> list:
        """
        Retrieve recent reports/context for the user.
        """
        if not email:
            return []

        key = f"ai_context:{email}:{mode}"

        def _op():
            return self._client.lrange(key, 0, limit - 1)

        return self._execute(_op, default_return=[])

    def save_ai_context(self, email: str, mode: str, report_text: str, limit: int = 3) -> bool:
        """
        Save the latest report/context to Redis, trimming to keep only the latest `limit` items.
        """
        if not email or not report_text:
            return False

        key = f"ai_context:{email}:{mode}"

        def _op():
            pipe = self._client.pipeline()
            pipe.lpush(key, report_text)
            pipe.ltrim(key, 0, limit - 1)
            pipe.expire(key, 604800) # Expire history after 7 days
            pipe.execute()
            return True

        return self._execute(_op, default_return=False)

    def get_chat_history(self, user_id: str, limit: int = 10) -> list:
        """
        Get chat history for a user. Returns a list of dicts chronological.
        """
        if not user_id:
            return []

        key = f"chat_history:{user_id}"

        def _op():
            raw_history = self._client.lrange(key, 0, limit - 1)
            import json
            history = []
            for item in raw_history:
                try:
                    history.append(json.loads(item))
                except:
                    pass
            history.reverse()
            return history

        return self._execute(_op, default_return=[])

    def save_chat_message(self, user_id: str, role: str, content: str, limit: int = 10) -> bool:
        """
        Save a chat message to the user's history list.
        """
        if not user_id or not content:
            return False

        key = f"chat_history:{user_id}"

        import json
        message_str = json.dumps({"role": role, "content": content}, ensure_ascii=False)

        def _op():
            pipe = self._client.pipeline()
            pipe.lpush(key, message_str)
            pipe.ltrim(key, 0, limit - 1)
            pipe.expire(key, 86400) # Keep history for 24 hours
            pipe.execute()
            return True

        return self._execute(_op, default_return=False)

    def get_user_cache(self, email: str):
        """
        Lấy thông tin user đã lưu trong Redis cache để tránh gọi Notion liên tục.
        """
        if not email:
            return None

        key = f"user_cache:{email.strip().lower()}"

        def _op():
            raw = self._client.get(key)
            if raw:
                import json
                try:
                    return json.loads(raw)
                except:
                    return None
            return None

        return self._execute(_op, default_return=None)

    def set_user_cache(self, email: str, user_data: dict, ttl_seconds: int = 86400 * 60) -> bool:
        """
        Lưu thông tin user vào Redis cache (mặc định 60 ngày) để duy trì phiên đăng nhập bền bỉ.
        """
        if not email or not user_data:
            return False

        key = f"user_cache:{email.strip().lower()}"
        import json

        def _op():
            val = json.dumps(user_data, ensure_ascii=False)
            return bool(self._client.set(key, val, ex=ttl_seconds))

        return self._execute(_op, default_return=False)


    def get_garmin_tokens(self, email: str) -> str:
        """
        Lấy Garmin OAuth token lưu trong Redis cache.
        """
        if not email:
            return None
        clean_email = email.strip().lower()
        key = f"garmin_tokens:{clean_email}"
        def _op():
            return self._client.get(key)
        return self._execute(_op, default_return=None)

    def save_garmin_tokens(self, email: str, token_str: str, ttl_seconds: int = 86400 * 30) -> bool:
        """
        Lưu Garmin OAuth token vào Redis (mặc định 30 ngày) để đăng nhập tức thì.
        """
        if not email or not token_str:
            return False
        clean_email = email.strip().lower()
        key = f"garmin_tokens:{clean_email}"
        def _op():
            return bool(self._client.set(key, token_str, ex=ttl_seconds))
        return self._execute(_op, default_return=False)

    def get_prompts_cache(self) -> dict:
        """
        Lấy cache prompts Notion từ Redis (tránh gọi Notion API mỗi lần).
        """
        key = "notion_prompts_cache"
        def _op():
            raw = self._client.get(key)
            if raw:
                import json
                try:
                    return json.loads(raw)
                except:
                    return None
            return None
        return self._execute(_op, default_return=None)

    def set_prompts_cache(self, prompts: dict, ttl_seconds: int = 3600) -> bool:
        """
        Lưu cache prompts Notion vào Redis (mặc định 1 giờ).
        """
        if not prompts:
            return False
        key = "notion_prompts_cache"
        import json
        def _op():
            val = json.dumps(prompts, ensure_ascii=False)
            return bool(self._client.set(key, val, ex=ttl_seconds))
        return self._execute(_op, default_return=False)

# Initialize a global Redis service instance
redis_service = RedisService()

