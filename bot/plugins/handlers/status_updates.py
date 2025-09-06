from structlog import get_logger
from pyrogram import Client
from pyrogram.types import ChatMemberUpdated

from utils.api_client import backend_client
from utils.chat_info_helper import get_chat_profile_update

log = get_logger(__name__)


@Client.on_chat_member_updated()
async def handle_bot_status_change(client: Client, update: ChatMemberUpdated):
    """
    Reacts to the bot's membership status changing and sends a full
    profile update to the backend.
    """
    if (update.old_chat_member and update.old_chat_member.user.id == client.me.id) or (
        update.new_chat_member and update.new_chat_member.user.id == client.me.id
    ):
        chat_id = update.chat.id
        log.info(
            "Bot membership status changed, fetching full profile.", chat_id=chat_id
        )

        profile_update = await get_chat_profile_update(client, chat_id)

        if profile_update:
            try:
                await backend_client.post(
                    "/analytics/chats/profiles/update",
                    json={"updates": [profile_update]},
                )
                log.info(
                    "Successfully sent real-time profile update to backend.",
                    chat_id=chat_id,
                )
            except Exception as e:
                log.error(
                    "Failed to send bot profile update to backend.",
                    error=str(e),
                    exc_info=True,
                )
