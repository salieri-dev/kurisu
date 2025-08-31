import redis.asyncio as redis
from config import settings

_redis_client = None


def get_redis_client() -> redis.Redis:
    """
    Factory function to create and reuse a single Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            str(settings.redis_url),
            password=settings.redis_password,
            decode_responses=True,
        )
    return _redis_client
