import base64
import io
from typing import Literal
import structlog
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit
from utils.help_registry import command_handler

log = structlog.get_logger(__name__)
ThreadType = Literal["bugurt", "greentext"]


async def _handle_thread_command(
    client: Client, message: Message, thread_type: ThreadType
):
    """Generic handler for both /bugurt and /greentext commands."""
    if len(message.command) < 2:
        await message.reply_text(
            f"❌ **Использование:** `/{thread_type} [тема]`", quote=True
        )
        return
    topic = message.text.split(maxsplit=1)[1]
    wait_msg = await message.reply_text("🧠 Генерирую тред...", quote=True)
    message.wait_msg = wait_msg
    response = await backend_client.post(
        f"/neuro/threads/{thread_type}",
        message=message,
        json={"topic": topic},
    )
    image_bytes = base64.b64decode(response["image_base64"])
    story_text = response["story"]
    caption = story_text
    if thread_type == "bugurt":
        normalized_text = story_text.replace("\n", "@")
        parts = [p.strip() for p in normalized_text.split("@") if p.strip()]
        caption = "\n@\n".join(parts)
    photo = io.BytesIO(image_bytes)
    photo.name = f"{thread_type}.png"
    await message.reply_photo(
        photo=photo, caption=caption, quote=True, parse_mode=ParseMode.DISABLED
    )
    await wait_msg.delete()


@Client.on_message(filters.command("bugurt"), group=1)
@command_handler(
    commands=["bugurt"],
    description="Генерирует тред в стиле /b/ Двача.",
    group="Нейронки",
    arguments="[тема]",
)
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
@command_handler(
    commands=["greentext"],
    description="Генерирует тред в стиле /b/ Форчана.",
    group="Нейронки",
    arguments="[тема]",
)
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
