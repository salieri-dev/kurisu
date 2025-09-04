"""Messages plugin for bot that sends all messages to Redis queue."""

import uuid
from datetime import UTC, datetime

import structlog
from opentelemetry import trace
from opentelemetry.propagate import inject
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from utils.message_utils import get_message_content, get_user_identifier
from utils.redis_utils import enqueue_message, serialize_message

log = structlog.get_logger(__name__)


@Client.on_message(filters.all, group=0)
async def message(client: Client, message):
    """Log all incoming messages to the queue for async processing."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("enqueue_message") as span:
        try:
            correlation_id = str(uuid.uuid4())
            message_data = serialize_message(message)
            message_data["correlation_id"] = correlation_id

            # Inject tracing context for the worker
            trace_context = {}
            inject(trace_context)
            message_data["trace_context"] = trace_context
            span.set_attribute("messaging.system", "redis")
            span.set_attribute("messaging.destination", "telegram_messages")
            span.set_attribute("messaging.message_id", message.id)

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
                "message enqueued",
                chat_title=chat_title,
                chat_id=message.chat.id,
                user_identifier=user_identifier,
                user_id=message.from_user.id if message.from_user else None,
                content=msg_content,
                correlation_id=correlation_id,
            )

        except Exception:
            log.exception("Error logging message")
