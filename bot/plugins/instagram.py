"""Instagram plugin that detects URLs and uses the backend to fetch media."""

import re

import structlog
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo, Message
from utils.api_client import backend_client
from utils.decorators import bind_context, rate_limit

log = structlog.get_logger(__name__)

INSTAGRAM_URL_PATTERN = r"https?://(?:www\.)?instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)"
GENERAL_ERROR = "❌ Не удалось загрузить пост из Instagram. Попробуйте позже."


def is_video(url: str) -> bool:
    """Check if an attachment URL is a video."""
    return ".mp4" in url or "_video_dashinit" in url


def smart_truncate(text: str, max_length: int = 250) -> str:
    """Intelligently truncates an Instagram description."""
    if not text:
        return ""
    core_content_lines = []
    lines = text.splitlines()
    for line in lines:
        stripped_line = line.strip()
        if re.fullmatch(r"^([_\W])\1*$", stripped_line) or re.fullmatch(
            r"^((\s*#\w+)+\s*)$", stripped_line
        ):
            break
        core_content_lines.append(line)
    processed_text = "\n".join(core_content_lines)
    processed_text = re.sub(r"#\w+", "", processed_text)
    promo_patterns = [r"\(TikTok\)", r"\(link in bio\)", r"follow @\w+"]
    for pattern in promo_patterns:
        processed_text = re.sub(pattern, "", processed_text, flags=re.IGNORECASE)
    processed_text = re.sub(r"\n{3,}", "\n\n", processed_text).strip()
    processed_text = re.sub(r" {2,}", " ", processed_text)
    if len(processed_text) <= max_length:
        return processed_text
    truncated_text = processed_text[:max_length]
    last_space = truncated_text.rfind(" ")
    return (
        truncated_text[:last_space] + "..."
        if last_space != -1
        else truncated_text + "..."
    )


@Client.on_message(filters.regex(INSTAGRAM_URL_PATTERN) & ~filters.channel, group=1)
@bind_context
@rate_limit(
    config_key_prefix="utilities/instagram.rate_limit",
    default_seconds=5,
    default_limit=2,
    key="user",
    silent=True,
)
async def instagram_handler(client: Client, message: Message):
    """Handles Instagram URLs by calling the backend to fetch and send media."""
    if not message.text:
        return
    match = re.search(INSTAGRAM_URL_PATTERN, message.text)
    if not match:
        return

    media_code = match.group(1)
    log.info("Instagram URL detected", media_code=media_code)

    response = await backend_client.get(
        f"/utilities/instagram/{media_code}", message=message
    )
    media = response["media"]

    raw_description = media.get("description", "") or ""
    truncated_desc = smart_truncate(raw_description)
    caption_parts = [
        "📱 **Пост из Instagram**",
        f"👤 **Автор:** [{media.get('author_name')}]({media.get('author_url')})",
    ]
    if truncated_desc:
        caption_parts.extend(["", f"📝 {truncated_desc}"])
    caption_parts.extend(
        [
            "",
            "📊 **Статистика:**",
            f"❤️ {media.get('likes', 0):,} лайков",
            f"💬 {media.get('comments', 0):,} комментариев",
            "",
            f"🔗 [Открыть в Instagram]({media.get('source_url')})",
        ]
    )
    caption = "\n".join(caption_parts)

    attachments = media.get("attachments", [])
    try:
        if not attachments:
            log.warning(
                "No attachments found for Instagram post", media_code=media_code
            )
            return

        if len(attachments) > 1:
            media_group = []
            for i, url in enumerate(attachments):
                media_item = (
                    InputMediaVideo(url) if is_video(url) else InputMediaPhoto(url)
                )
                if i == 0:
                    media_item.caption = caption
                media_group.append(media_item)
            await message.reply_media_group(media=media_group, quote=True)
        else:
            url = attachments[0]
            if is_video(url):
                await message.reply_video(video=url, caption=caption, quote=True)
            else:
                await message.reply_photo(photo=url, caption=caption, quote=True)
        log.info("Successfully sent Instagram media to chat", media_code=media_code)

    except Exception as e:
        log.error(
            "Error sending Instagram media to Telegram",
            media_code=media_code,
            error=str(e),
            exc_info=True,
        )
