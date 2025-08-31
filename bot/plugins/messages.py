"""Messages plugin for bot that sends all messages to Redis queue."""
from datetime import UTC, datetime

import structlog
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from utils.message_utils import get_message_content, get_user_identifier
from utils.redis_utils import enqueue_message, serialize_message

log = structlog.get_logger(__name__)


@Client.on_message(filters.all, group=0)
async def message(client: Client, message):
    """Log all incoming messages to the queue for async processing."""
    try:
        message_data = serialize_message(message)

        message_data["date"] = message.date
        message_data["created_at"] = datetime.now(UTC)

        if not await enqueue_message(message_data):
            log.warning("Failed to enqueue message", message_id=message.id)

        user_identifier = get_user_identifier(message)
        msg_content = get_message_content(message)
        chat_title = (
            "DM" if message.chat.type == ChatType.PRIVATE else message.chat.title
        )

        log.info(
            "message received",
            chat_title=chat_title,
            chat_id=message.chat.id,
            user_identifier=user_identifier,
            user_id=message.from_user.id if message.from_user else None,
            content=msg_content,
        )

    except Exception as e:
        log.error("Error logging message", error=str(e), exc_info=True)
