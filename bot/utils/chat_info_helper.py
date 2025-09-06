import json
from pyrogram import Client
from pyrogram.types import Chat
from structlog import get_logger

log = get_logger(__name__)


def serialize_chat_object(chat: Chat) -> dict:
    """
    Serializes a Pyrogram Chat object into a JSON-compatible dictionary.
    Handles nested objects and enums.
    """
    return json.loads(str(chat))


async def get_chat_profile_update(client: Client, chat_id: int) -> dict | None:
    """
    Fetches full chat info and the bot's member status for a given chat_id.
    Returns a dictionary ready to be sent to the backend API.
    """
    try:
        chat = await client.get_chat(chat_id)
        chat_info = serialize_chat_object(chat)

        member = await client.get_chat_member(chat_id, client.me.id)
        status = member.status.name

        return {"chat_id": chat_id, "status": status, "chat_info": chat_info}
    except Exception as e:
        log.warn(
            "Could not fetch full chat info, sending minimal update.",
            chat_id=chat_id,
            error=str(e),
        )
        return {
            "chat_id": chat_id,
            "status": "LEFT",
            "chat_info": {"id": chat_id, "title": "Inaccessible Chat"},
        }
