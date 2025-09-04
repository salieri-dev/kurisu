import shlex

import structlog
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, owner_only

log = structlog.get_logger(__name__)


@Client.on_message(filters.command("debug"), group=1)
@owner_only
@handle_api_errors
async def debug_command(client: Client, message: Message):
    """
    Parses arguments and calls the backend debug endpoint.
    Example: /debug level=error delay=1.5 code=503 spans=true
    """
    payload = {
        "log_level": "info",
        "log_message": "This is a test log from the /debug command.",
        "http_status_code": 200,
        "delay_seconds": 0,
        "create_spans": False,
    }

    try:
        args = shlex.split(
            message.text.split(" ", 1)[1] if len(message.command) > 1 else ""
        )
        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                key = key.lower()
                if key in ["level", "log_level"]:
                    payload["log_level"] = value
                elif key in ["msg", "message", "log_message"]:
                    payload["log_message"] = value
                elif key in ["code", "http_status_code"]:
                    payload["http_status_code"] = int(value)
                elif key in ["delay", "delay_seconds"]:
                    payload["delay_seconds"] = float(value)
                elif key in ["spans", "create_spans"]:
                    payload["create_spans"] = value.lower() in ["true", "1", "yes"]
    except Exception as e:
        await message.reply_text(f"❌ Invalid argument format: {e}", quote=True)
        return

    await backend_client.post(
        "/utilities/debug/generate", message=message, json=payload
    )

    await message.reply_text(
        "✅ **Debug event generated successfully!**\n\n"
        "Check Grafana, Loki, and Jaeger to see the results.\n\n"
        f"**Payload sent:**\n```json\n{payload}\n```",
        quote=True,
    )
