from io import BytesIO
from typing import Tuple, Optional
from pyrogram.types import Message
from structlog import get_logger

log = get_logger(__name__)

SUPPORTED_MIMES = ["image/jpeg", "image/png", "image/webp"]
GIF_MIMES = ["video/mp4", "image/gif"]


async def get_media_as_bytes(message: Message) -> Optional[Tuple[BytesIO, bool]]:
    """
    Retrieves media from a message or its reply as a BytesIO object.

    Handles photos, stickers, animations, documents, and now also
    voice messages, audio files, and video notes.

    Returns:
        A tuple of (BytesIO, is_gif) or None if no valid media is found.
    """
    target_message = message.reply_to_message or message

    media_obj = (
        target_message.voice
        or target_message.audio
        or target_message.video_note
        or target_message.photo
        or target_message.sticker
        or target_message.animation
        or target_message.video
        or target_message.document
    )

    if not media_obj:
        return None

    is_gif = False
    is_transcribable_media = hasattr(media_obj, "duration")

    if hasattr(media_obj, "mime_type"):
        if media_obj.mime_type in GIF_MIMES:
            is_gif = True
        elif not is_transcribable_media and media_obj.mime_type not in SUPPORTED_MIMES:
            log.warning(
                "Unsupported document MIME type for image processing",
                mime=media_obj.mime_type,
            )
            return None

    if hasattr(media_obj, "is_animated") and media_obj.is_animated:
        is_gif = True

    try:
        in_memory_file = await target_message.download(in_memory=True)
        if isinstance(in_memory_file, BytesIO):
            return in_memory_file, is_gif
    except Exception as e:
        log.error("Failed to download media in-memory", error=str(e))
        return None

    return None
