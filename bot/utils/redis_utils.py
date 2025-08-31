import json

import redis.asyncio as redis
import structlog
from config import credentials
from redis.asyncio import Redis

log = structlog.get_logger(__name__)


def create_redis_client() -> Redis:
    """Factory to create a Redis client using centralized config."""
    return redis.from_url(
        str(credentials.redis_url),
        password=credentials.redis_password,
        decode_responses=True,
    )


redis_client = create_redis_client()


def serialize_message(obj: object) -> dict:
    """Serialize message objects to JSON-compatible dictionaries."""
    return json.loads(str(obj))


async def enqueue_message(message_data: dict) -> bool:
    """
    Enqueue a message for async processing.

    Args:
        message_data: Message data to enqueue

    Returns:
        bool: True if successfully enqueued, False otherwise
    """
    try:
        queue_name = "telegram_messages"
        message_json = json.dumps(message_data, default=str)
        await redis_client.lpush(queue_name, message_json)
        return True

    except Exception as e:
        log.error("Failed to enqueue message", error=str(e), exc_info=True)
        return False
