# bot/plugins/threads.py

import base64
import io
from typing import Literal

import structlog
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit

log = structlog.get_logger(__name__)

ThreadType = Literal["bugurt", "greentext"]


async def _handle_thread_command(client: Client, message: Message, thread_type: ThreadType):
    """Generic handler for both /bugurt and /greentext commands."""
    if len(message.command) < 2:
        await message.reply_text(f"❌ **Использование:** `/{thread_type} [тема]`", quote=True)
        return

    topic = message.text.split(maxsplit=1)[1]
    
    notification = await message.reply_text("🧠 Генерирую тред...", quote=True)

    response = await backend_client.post(
        f"/neuro/threads/{thread_type}",
        message=message,
        json={"topic": topic},
    )

    image_bytes = base64.b64decode(response["image_base64"])
    story_text = response["story"]

    photo = io.BytesIO(image_bytes)
    photo.name = f"{thread_type}.png"

    await message.reply_photo(photo=photo, caption=story_text, quote=True)
    await notification.delete()


@Client.on_message(filters.command("bugurt"), group=1)
@rate_limit(
    config_key_prefix="neuro/threads.bugurt.rate_limit",
    default_seconds=60,
    default_limit=2,
    key="user",
)
@nsfw_guard
@handle_api_errors
async def bugurt_command(client: Client, message: Message):
    """Handler for /bugurt command."""
    await _handle_thread_command(client, message, "bugurt")


@Client.on_message(filters.command("greentext"), group=1)
@rate_limit(
    config_key_prefix="neuro/threads.greentext.rate_limit",
    default_seconds=60,
    default_limit=2,
    key="user",
)
@nsfw_guard
@handle_api_errors
async def greentext_command(client: Client, message: Message):
    """Handler for /greentext command."""
    await _handle_thread_command(client, message, "greentext")