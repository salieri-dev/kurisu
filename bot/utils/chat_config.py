
from typing import Any

import structlog
from pyrogram.enums import ChatType
from pyrogram.types import Message

from .api_client import backend_client
from .redis_utils import redis_client

log = structlog.get_logger(__name__)


async def get_chat_config(message: Message, key: str, default: Any = None) -> Any:
    """
    Fetches a specific configuration value for a chat using a cache-aside strategy.

    This is the central, reusable function for all chat-specific settings.

    Args:
        message: The Pyrogram message object.
        key: The configuration key to fetch (e.g., 'nsfw_enabled').
        default: The value to return if the key is not found or an error occurs.

    Returns:
        The configuration value, or the default if not found.
    """
    if message.chat.type == ChatType.PRIVATE:
        return default if default is not None else True

    cache_key = f"chat_config:{message.chat.id}:{key}"

    try:
        cached_value = await redis_client.get(cache_key)
        if cached_value is not None:
            return cached_value == "1" if isinstance(default, bool) else cached_value
    except Exception:
        log.warning("Redis check failed for chat config, falling back to API.", key=key)

    try:
        response = await backend_client.get(
            f"/core/chat_config/{message.chat.id}/{key}", message=message
        )
        api_value = response.get("param_value", default)

        value_to_cache = "1" if api_value else "0"
        await redis_client.set(cache_key, value_to_cache, ex=300)

        return api_value
    except Exception:
        log.error(
            "API call for chat config failed, returning safe default.",
            key=key,
            default_value=default,
        )
        return default
