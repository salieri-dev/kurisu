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


# bot/utils/message_utils.py
from collections.abc import Generator

# (Other functions like get_user_identifier can remain here)

MAX_MESSAGE_LENGTH = 4096


def split_message(text: str) -> Generator[str, None, None]:
    """
    Splits a long text into multiple chunks, each under Telegram's message length limit.

    This function attempts to split text at the most logical points in the following order:
    1. Paragraphs (double newlines)
    2. Sentences (followed by a newline)
    3. Words (spaces)
    4. As a last resort, hard cuts the text at the character limit.

    Args:
        text: The string to be split.

    Yields:
        A generator of strings, where each string is a message chunk.
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        yield text
        return

    while len(text) > 0:
        # If the remaining text is within the limit, yield it and finish.
        if len(text) <= MAX_MESSAGE_LENGTH:
            yield text
            break

        # Find the best possible split point within the allowed length.
        chunk = text[:MAX_MESSAGE_LENGTH]
        split_pos = -1

        # Prefer splitting at the last double newline (paragraph).
        last_double_newline = chunk.rfind("\n\n")
        if last_double_newline != -1:
            split_pos = last_double_newline + 2  # Include the newlines in the split
        else:
            # Otherwise, split at the last single newline.
            last_newline = chunk.rfind("\n")
            if last_newline != -1:
                split_pos = last_newline + 1
            else:
                # Otherwise, split at the last space.
                last_space = chunk.rfind(" ")
                if last_space != -1:
                    split_pos = last_space + 1
                else:
                    # If no good split point is found, do a hard cut.
                    split_pos = MAX_MESSAGE_LENGTH

        # Yield the chunk and update the remaining text.
        yield text[:split_pos]
        text = text[split_pos:]
