from pyrogram.enums import ChatType


def get_user_identifier(message) -> str:
    """Extract user identifier from message."""
    if message.from_user is None:
        return "Channel" if message.chat.type == ChatType.CHANNEL else "Unknown"

    user = message.from_user
    return user.username or user.first_name or user.last_name or "Unknown User"


def get_message_content(message) -> str:
    """Extract and format message content."""
    content = message.text or message.caption or "None"
    content = content.replace("\n", " ").strip()

    if message.media:
        media_type = str(message.media).replace("MessageMediaType.", "")
        content += f" [{media_type}]"

    if message.service:
        message_service = str(message.service).replace("MessageServiceType.", "")
        content += f" [{message_service}]"

    return content
