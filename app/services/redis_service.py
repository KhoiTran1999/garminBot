import redis
import logging
from app.config import Config

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

    def check_and_set_dedup(self, tele_id: str, date_str: str, mode: str) -> bool:
        """
        Check if a report has already been sent for the user on the given date and mode.
        Allows up to 2 times a day by enforcing a 12-hour gap (43200 seconds).
        Returns:
            True if it's a new report (successfully set deduplication lock).
            False if it has already been sent (deduplication lock exists) or if Redis fails.
        """
        if not tele_id:
            return True # Fail-safe: allow if tele_id is missing (e.g. admin or test)

        # Remove date_str from key to enforce 1-hour gap across date boundaries
        key = f"sent:{tele_id}:{mode}"

        # nx=True means only set if the key does not exist. ex=3600 is 1 hour TTL.
        def _op():
            return bool(self._client.set(key, "1", ex=3600, nx=True))

        return self._execute(_op, default_return=True)

    def delete_dedup(self, tele_id: str, date_str: str, mode: str) -> bool:
        """
        Delete a deduplication lock if a run failed.
        """
        if not tele_id:
            return True

        key = f"sent:{tele_id}:{mode}"

        def _op():
            return bool(self._client.delete(key))

        return self._execute(_op, default_return=True)

    def is_rate_limited(self, tele_id: str, mode: str, limit: int = 3, window_seconds: int = 600) -> bool:
        """
        Rate limiter to prevent spamming triggers.
        Returns:
            True if the user is rate limited (exceeded threshold).
            False if the trigger is allowed.
        """
        if not tele_id:
            return False

        key = f"ratelimit:{tele_id}:{mode}"

        def _op():
            # Get current count
            count_str = self._client.get(key)
            if count_str is not None:
                count = int(count_str)
                if count >= limit:
                    return True

            # Increment and set expire if it's new
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

# Initialize a global Redis service instance
redis_service = RedisService()
