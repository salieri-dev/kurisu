import functools
import uuid
from typing import Any, Literal

import structlog
from config import credentials
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType
from utils.chat_config import get_chat_config

from .config_client import get_config
from .exceptions import APIError
from .redis_utils import redis_client

log = structlog.get_logger(__name__)

OWNER_ID = credentials.owner_id


def owner_only(func):
    """
    A decorator to restrict a command to the bot owner.

    If an unauthorized user tries to execute the command, it logs a warning
    and silently ignores the request, providing no feedback to the user.
    """

    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if not message.from_user:
            return

        if message.from_user.id == OWNER_ID:
            return await func(client, message, *args, **kwargs)
        else:
            log.warning(
                "Unauthorized access attempt to owner-only command",
                user_id=message.from_user.id,
                username=message.from_user.username or "N/A",
                command_text=message.text,
            )
            return

    return wrapper


def handle_api_errors(func):
    """
    Decorator to catch and handle APIError exceptions.
    It formats a user-friendly error message and will EDIT the bot's last "wait"
    message if available, otherwise it will send a new reply.
    """

    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except APIError as e:
            log.error(
                "APIError caught by handler", func_name=func.__name__, error=str(e)
            )

            user_message = "❌ **Произошла неожиданная ошибка с сервером**"
            if e.correlation_id:
                user_message += f"\n\nID ошибки для разработчика @not_salieri: ||`{e.correlation_id}`||"

            wait_msg = getattr(message, "wait_msg", None)

            try:
                if wait_msg:
                    await wait_msg.edit_text(user_message)
                else:
                    await message.reply_text(user_message, quote=True)
            except Exception as edit_error:
                # If editing fails (e.g., message was deleted), send a new message
                log.warning(
                    "Failed to edit wait message, sending new reply",
                    error=str(edit_error),
                )
                try:
                    await message.reply_text(user_message, quote=True)
                except Exception as reply_error:
                    log.error("Failed to send error message", error=str(reply_error))
            return
        except Exception as e:
            log.exception(
                "Unhandled exception in command handler",
                func_name=func.__name__,
                error=str(e),
            )

            error_message = "🔧 Произошла непредвиденная внутренняя ошибка. Разработчики уже уведомлены."
            wait_msg = getattr(message, "wait_msg", None)

            try:
                if wait_msg:
                    await wait_msg.edit_text(error_message)
                else:
                    await message.reply_text(error_message, quote=True)
            except Exception as edit_error:
                log.warning(
                    "Failed to edit wait message, sending new reply",
                    error=str(edit_error),
                )
                try:
                    await message.reply_text(error_message, quote=True)
                except Exception as reply_error:
                    log.error("Failed to send error message", error=str(reply_error))
            return

    return wrapper


def bind_context(func):
    """
    Decorator to bind essential message context to structlog's contextvars.
    This ensures that all logs generated within a handler are tagged with
    relevant information like user_id, chat_id, and a unique trace_id.
    """

    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            user_id=message.from_user.id if message.from_user else None,
            user_name=message.from_user.username if message.from_user else None,
            chat_id=message.chat.id,
            message_id=message.id,
            trace_id=str(uuid.uuid4()),
        )
        try:
            return await func(client, message, *args, **kwargs)
        finally:
            structlog.contextvars.clear_contextvars()

    return wrapper


def rate_limit(
    config_key_prefix: str,
    default_seconds: int,
    default_limit: int,
    key: Literal["user", "chat"] = "user",
    silent: bool = False,
):
    """
    A decorator factory for rate-limiting commands based on dynamic config.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            seconds = await get_config(
                f"{config_key_prefix}.seconds",
                message,
                default=default_seconds,
                description=f"Rate limit window in seconds for {func.__name__}.",
            )
            limit = await get_config(
                f"{config_key_prefix}.limit",
                message,
                default=default_limit,
                description=f"Number of allowed requests in the window for {func.__name__}.",
            )

            if key == "user":
                if not message.from_user:
                    return
                key_id = message.from_user.id
            else:
                key_id = message.chat.id

            redis_key = f"ratelimit:{func.__name__}:{key}:{key_id}"

            try:
                request_count = await redis_client.incr(redis_key)
                if request_count == 1:
                    await redis_client.expire(redis_key, seconds)

                if request_count > limit:
                    ttl = await redis_client.ttl(redis_key)

                    log.info(
                        "Rate limit exceeded",
                        func_name=func.__name__,
                        rate_limit_key=key,
                        key_id=key_id,
                        ttl=ttl,
                        request_count=request_count,
                        command=message.text,
                    )
                    if not silent and ttl > 0:
                        await message.reply_text(
                            f"⏳ Пожалуйста, подождите {ttl} секунд перед повторным использованием этой команды."
                        )
                    return
            except Exception:
                log.exception("Redis error in rate limiter, failing open")
                pass

            return await func(client, message, *args, **kwargs)

        return wrapper

    return decorator


def require_chat_config(
    key: str,
    expected_value: Any = True,
    error_message: str = "❌ Эта команда отключена в этом чате.",
):
    """
    A generic decorator to guard commands based on chat configuration.
    This check is SKIPPED in private messages.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            if message.chat.type == ChatType.PRIVATE:
                return await func(client, message, *args, **kwargs)

            current_value = await get_chat_config(message, key, default=False)

            if current_value == expected_value:
                return await func(client, message, *args, **kwargs)
            else:
                log.warning(
                    "Command blocked by require_chat_config guard",
                    func_name=func.__name__,
                    chat_id=message.chat.id,
                    required_key=key,
                )
                await message.reply_text(error_message, quote=True)
                return

        return wrapper

    return decorator


nsfw_guard = require_chat_config(
    key="nsfw_enabled",
    expected_value=True,
    error_message=(
        "🔞 Эта команда отключена, так как NSFW-контент запрещен в этом чате.\n"
        "Администратор может включить его с помощью команды `/config enable nsfw`."
    ),
)
