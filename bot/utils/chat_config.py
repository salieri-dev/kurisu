# Path: bot/utils/chat_config.py

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
    # Settings don't apply in private chats; always return the safe default (or True if default is True)
    if message.chat.type == ChatType.PRIVATE:
        return default if default is not None else True

    cache_key = f"chat_config:{message.chat.id}:{key}"

    # 1. Try to get from cache
    try:
        cached_value = await redis_client.get(cache_key)
        if cached_value is not None:
            # Redis stores everything as strings, so '0' becomes False, '1' becomes True.
            return cached_value == "1" if isinstance(default, bool) else cached_value
    except Exception:
        log.warning("Redis check failed for chat config, falling back to API.", key=key)

    # 2. Cache miss or failure, get from API
    try:
        response = await backend_client.get(
            f"/core/chat_config/{message.chat.id}/{key}", message=message
        )
        # The API returns the value, or `null` if not set.
        api_value = response.get("param_value", default)

        # 3. Cache the result for next time
        value_to_cache = "1" if api_value else "0"
        await redis_client.set(cache_key, value_to_cache, ex=300)  # 5-minute cache

        return api_value
    except Exception:
        log.error(
            "API call for chat config failed, returning safe default.",
            key=key,
            default_value=default,
        )
        return default
