"""Messages plugin for bot that sends all messages to the backend API."""

import json
import uuid
from datetime import UTC, datetime
import structlog
from opentelemetry import trace
from opentelemetry.propagate import inject
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from utils.api_client import backend_client
from utils.message_utils import get_message_content, get_user_identifier

log = structlog.get_logger(__name__)


def serialize_message(obj: object) -> dict:
    """Serialize message objects to JSON-compatible dictionaries."""
    return json.loads(str(obj))


@Client.on_message(filters.all, group=0)
async def message(client: Client, message):
    """Log all incoming messages by sending them to the backend API."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("save_message_via_api") as span:
        try:
            correlation_id = str(uuid.uuid4())
            message_data = serialize_message(message)

            message_data["correlation_id"] = correlation_id
            message_data["created_at"] = datetime.now(UTC).isoformat()

            trace_context = {}
            inject(trace_context)
            message_data["trace_context"] = trace_context

            span.set_attribute("http.method", "POST")
            span.set_attribute(
                "http.url", f"{backend_client._client.base_url}/core/messages/save"
            )
            span.set_attribute("messaging.message_id", message.id)

            await backend_client.post(
                "/core/messages/save", message=message, json=message_data
            )

            user_identifier = get_user_identifier(message)
            msg_content = get_message_content(message)
            chat_title = (
                "DM" if message.chat.type == ChatType.PRIVATE else message.chat.title
            )
            log.info(
                "Message sent to backend API",
                chat_title=chat_title,
                chat_id=message.chat.id,
                user_identifier=user_identifier,
                user_id=message.from_user.id if message.from_user else None,
                content=msg_content,
                correlation_id=correlation_id,
            )
        except Exception:
            log.exception("Failed to send message to backend API")
