from datetime import datetime, timedelta
import asyncio
import pytz
from pyrogram import Client
from pyrogram.enums import ChatType
from structlog import get_logger
from utils.api_client import backend_client
from utils.message_utils import split_message
from utils.chat_config import get_chat_config
from utils.exceptions import APIError

log = get_logger(__name__)
MOSCOW_TZ = pytz.timezone("Europe/Moscow")


class SummaryJob:
    """Scheduled job to generate and send daily chat summaries."""

    def __init__(self, client: Client):
        self.client = client

    async def run_daily_summary(self):
        """The main logic for the daily summary job."""
        yesterday = datetime.now(MOSCOW_TZ) - timedelta(days=1)
        log.info(
            "Starting daily summary generation job", date=yesterday.strftime("%Y-%m-%d")
        )

        try:
            enabled_chats = []
            async for dialog in self.client.get_dialogs():
                if dialog.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    is_enabled = await get_chat_config(
                        message=dialog.chat, key="summary_enabled", default=False
                    )
                    if is_enabled:
                        enabled_chats.append(dialog.chat)

            if not enabled_chats:
                log.info("No chats with summaries enabled. Job finished.")
                return

            log.info(
                f"Found {len(enabled_chats)} chats with summaries enabled.",
                chats=[c.id for c in enabled_chats],
            )

            for chat in enabled_chats:
                try:
                    log.info(
                        "Generating summary for chat",
                        chat_id=chat.id,
                        chat_title=chat.title,
                    )
                    payload = {
                        "chat_id": chat.id,
                        "chat_title": chat.title or "Unknown Chat",
                        "date": yesterday.strftime("%Y-%m-%d"),
                    }
                    response = await backend_client.post(
                        "/neuro/summary/generate", json=payload
                    )

                    for part in split_message(response["formatted_text"]):
                        await self.client.send_message(
                            chat_id=chat.id, text=part, disable_web_page_preview=True
                        )
                    log.info("Successfully sent summary to chat", chat_id=chat.id)
                    await asyncio.sleep(5)
                except APIError as e:
                    log.warning(
                        "API error while generating summary for chat",
                        chat_id=chat.id,
                        status_code=e.status_code,
                        detail=e.detail,
                        correlation_id=e.correlation_id,
                    )
                except Exception as e:
                    log.error(
                        "Failed to process summary for one chat",
                        chat_id=chat.id,
                        error=str(e),
                        exc_info=True,
                    )

            log.info("Daily summary job completed.")
        except Exception as e:
            log.error(
                "Daily summary job failed critically", error=str(e), exc_info=True
            )
