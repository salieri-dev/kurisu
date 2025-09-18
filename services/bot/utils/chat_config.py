from typing import Any
import structlog
from pyrogram.enums import ChatType
from pyrogram.types import Message
from .api_client import backend_client

log = structlog.get_logger(__name__)


async def get_chat_config(message: Message, key: str, default: Any = None) -> Any:
    """
    Fetches a specific configuration value for a chat directly from the backend API.
    The backend is the single source of truth for configuration.
    Args:
        message: The Pyrogram message object.
        key: The configuration key to fetch (e.g., 'nsfw_enabled').
        default: The value to return if the key is not found or an error occurs.
    Returns:
        The configuration value, or the default if not found.
    """
    if message.chat.type == ChatType.PRIVATE:
        return default if default is not None else True

    try:
        response = await backend_client.get(
            f"/core/chat_config/{message.chat.id}/{key}", message=message
        )
        return response.get("param_value", default)
    except Exception:
        log.error(
            "API call for chat config failed, returning safe default.",
            key=key,
            chat_id=message.chat.id,
            default_value=default,
            exc_info=True,
        )
        return default
