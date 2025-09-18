import re
from typing import List

from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, Message
from structlog import get_logger

from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit
from utils.help_registry import command_handler

log = get_logger(__name__)

NHENTAI_URL_PATTERN = r"https?://nhentai\.net/g/(\d+)"


async def send_album(message: Message, response: dict):
    """Helper function to send a media group album from backend response."""
    caption = response["caption"]
    image_urls = response["image_urls"]

    if not image_urls:
        await message.reply_text(
            "❌ Не удалось получить изображения для этой галереи.", quote=True
        )
        return

    album: List[InputMediaPhoto] = [
        InputMediaPhoto(media=url, caption=caption if i == 0 else None)
        for i, url in enumerate(image_urls)
    ]

    await message.reply_media_group(media=album, quote=True)


@Client.on_message(filters.command("nhentai"), group=1)
@command_handler(
    commands=["nhentai"],
    description="Присылает случайную додзинси с nhentai.",
    group="NSFW",
)
@nsfw_guard
@rate_limit("fun/nhentai.rate_limit", 5, 1)
@handle_api_errors
async def nhentai_cmd(client: Client, message: Message):
    """Handles the /nhentai command for a random gallery."""
    wait_msg = await message.reply_text("🎲 Ищу случайную додзинси...", quote=True)
    message.wait_msg = wait_msg

    response = await backend_client.get("/fun/nhentai/random", message=message)
    await send_album(message, response)

    await wait_msg.delete()


@Client.on_message(filters.regex(NHENTAI_URL_PATTERN), group=1)
@nsfw_guard
@handle_api_errors
async def nhentai_url_handler(client: Client, message: Message):
    """Handles nhentai URLs posted in chat."""
    match = re.search(NHENTAI_URL_PATTERN, message.text)
    if not match:
        return

    gallery_id = int(match.group(1))
    response = await backend_client.get(
        f"/fun/nhentai/gallery/{gallery_id}", message=message
    )
    await send_album(message, response)
