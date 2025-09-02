# Path: backend/utils/redis_client.py

import redis.asyncio as redis
from config import settings

_redis_client: redis.Redis | None = None


async def init_redis_client() -> redis.Redis:
    """
    Creates and initializes the Redis client connection pool.
    This function is called once during the application's startup lifespan.
    """
    global _redis_client
    _redis_client = redis.from_url(
        str(settings.redis_url),
        password=settings.redis_password,
        decode_responses=True,
    )
    # Verify the connection is active.
    await _redis_client.ping()
    return _redis_client


async def close_redis_client():
    """
    Closes the Redis client connection pool gracefully.
    This function is called once during the application's shutdown lifespan.
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()


# The dependency function `get_redis_client` is now moved to `dependencies.py`
# to keep all injectable dependencies in one place.
