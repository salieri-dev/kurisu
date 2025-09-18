import json
import structlog
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.chat_config import get_chat_config
from utils.config_client import get_config
from utils.decorators import handle_api_errors, rate_limit
from utils.media_helpers import get_media_as_bytes

log = structlog.get_logger(__name__)
TRANSCRIPTION_SUCCESS_TPL = "\n>💭 {}"


@Client.on_message(filters.voice | filters.audio | filters.video_note, group=3)
@rate_limit(
    config_key_prefix="utilities/transcribe.rate_limit",
    default_seconds=10,
    default_limit=1,
    key="user",
)
@handle_api_errors
async def transcribe_handler(client: Client, message: Message):
    """Handle voice, audio, and video notes for transcription."""
    if not message.from_user:
        return
    if message.chat.type != ChatType.PRIVATE:
        is_enabled = await get_chat_config(
            message, key="transcribe_enabled", default=True
        )
        if not is_enabled:
            return
    media = message.voice or message.audio or message.video_note
    if not media or not hasattr(media, "duration"):
        return
    duration = media.duration
    min_duration = await get_config(
        "utilities/transcribe.min_duration_seconds", message, 5
    )
    max_duration = await get_config(
        "utilities/transcribe.max_duration_seconds", message, 600
    )
    if not (min_duration <= duration <= max_duration):
        log.info(
            "Audio duration out of configured bounds, skipping.",
            duration=duration,
            chat_id=message.chat.id,
        )
        return
    log.info(
        "Processing audio for transcription", chat_id=message.chat.id, duration=duration
    )
    media_data = await get_media_as_bytes(message)
    if not media_data:
        log.warning(
            "Could not extract media bytes from message.", message_id=message.id
        )
        return
    media_bytes, _ = media_data
    file_name = getattr(media, "file_name", "audio.ogg")
    mime_type = getattr(media, "mime_type", "audio/ogg")
    response_bytes, _ = await backend_client.post_media(
        "/utilities/transcribe",
        message=message,
        file_bytes=media_bytes,
        file_name=file_name,
        file_mime=mime_type,
        data={"duration": str(duration)},
    )
    json_response = json.loads(response_bytes.decode("utf-8"))
    transcription = json_response.get("transcription")
    if transcription:
        log.info("Transcription successful", length=len(transcription))
        await message.reply_text(
            TRANSCRIPTION_SUCCESS_TPL.format(transcription), quote=True
        )
