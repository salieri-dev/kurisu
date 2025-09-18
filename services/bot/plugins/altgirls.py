import base64
import io
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, Message
from structlog import get_logger
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit
from utils.help_registry import command_handler

log = get_logger(__name__)
NO_IMAGES_FOUND = "Изображения не найдены."
GENERAL_ERROR = "❌ Произошла ошибка! Попробуйте позже."


def format_source_link(source_link: str) -> str:
    """Formats the source link into a clickable markdown link."""
    if "://" in source_link:
        if "vk.com/" in source_link:
            username = source_link.split("vk.com/")[1].split("/")[0]
            if username:
                return f"[{username}]({source_link})"
        elif "t.me/" in source_link:
            username = source_link.split("t.me/")[1].split("/")[0]
            if username:
                return f"[{username}]({source_link})"
        return source_link
    if "_" not in source_link:
        return f"Неизвестно (источник: {source_link})"
    platform, username = source_link.split("_", 1)
    if platform == "tg":
        return f"[{username}](https://t.me/{username})"
    elif platform == "vk":
        return f"[{username}](https://vk.com/{username})"
    else:
        return f"Неизвестно (источник: {source_link})"


@Client.on_message(filters.command(["altgirls"]), group=1)
@command_handler(
    commands=["altgirls"],
    description="Присылает 4 рандомных пикчи альтушек.",
    group="NSFW",
)
@rate_limit(
    config_key_prefix="fun/altgirls.rate_limit",
    default_seconds=3,
    default_limit=1,
    key="user",
    silent=False,
)
@nsfw_guard
@handle_api_errors
async def handle_altgirls(client: Client, message: Message):
    """Handle /altgirls command: fetch images from backend and send with source links."""
    count = 4
    wait_msg = await message.reply_text("🔍 Запрашиваем альтушек...", quote=True)
    message.wait_msg = wait_msg
    result = await backend_client.get(
        "/fun/altgirls",
        message=message,
        params={"n": count},
    )
    images = result.get("images", [])
    if not images:
        await wait_msg.edit_text(NO_IMAGES_FOUND)
        return
    caption_parts = ["**Источники:**"]
    for i, img in enumerate(images, 1):
        source_raw = img.get("source_link", "Неизвестно")
        source_formatted = format_source_link(source_raw)
        caption_parts.append(f"{i}. {source_formatted}")
    combined_caption = "\n".join(caption_parts)
    media_group = []
    for idx, img in enumerate(images):
        raw = base64.b64decode(img["base64_data"])
        bio = io.BytesIO(raw)
        bio.name = img.get("filename") or f"image_{idx + 1}.jpg"
        if idx == 0:
            media_group.append(InputMediaPhoto(media=bio, caption=combined_caption))
        else:
            media_group.append(InputMediaPhoto(media=bio))
    if not media_group:
        await wait_msg.edit_text(GENERAL_ERROR)
        return
    await message.reply_media_group(media=media_group, quote=True)
    await wait_msg.delete()
