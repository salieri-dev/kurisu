import functools
import uuid
from typing import Literal

import structlog
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.types import Message

from .api_client import backend_client
from .config_client import get_config
from .exceptions import APIError
from .redis_utils import redis_client

log = structlog.get_logger(__name__)


def handle_api_errors(func):
    """
    Decorator to catch and handle APIError exceptions from the backend client.
    It formats a user-friendly error message, including a correlation ID.
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

            await message.reply_text(user_message, quote=True)
            return
        except Exception as e:
            log.exception(
                "Unhandled exception in command handler",
                func_name=func.__name__,
                error=str(e),
            )
            await message.reply_text(
                "🔧 Произошла непредвиденная внутренняя ошибка. Разработчики уже уведомлены.",
                quote=True,
            )
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


def nsfw_guard(func):
    """
    A decorator that guards a command based on chat settings.
    It uses a Redis cache to avoid frequent API calls.
    """

    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if message.chat.type == ChatType.PRIVATE:
            return await func(client, message, *args, **kwargs)

        cache_key = f"chat_config:{message.chat.id}:nsfw_enabled"
        nsfw_enabled = False

        try:
            cached_value = await redis_client.get(cache_key)

            if cached_value is not None:
                nsfw_enabled = cached_value == "1"
                log.debug(
                    "NSFW guard cache hit",
                    chat_id=message.chat.id,
                    nsfw_enabled=nsfw_enabled,
                )
            else:
                log.debug("NSFW guard cache miss, calling API", chat_id=message.chat.id)
                response = await backend_client.get(
                    f"/core/chat_config/{message.chat.id}/nsfw_enabled", message=message
                )
                api_value = response.get("param_value") or False
                nsfw_enabled = bool(api_value)

                await redis_client.set(cache_key, "1" if nsfw_enabled else "0", ex=300)
                log.info(
                    "NSFW config cached",
                    chat_id=message.chat.id,
                    nsfw_enabled=nsfw_enabled,
                )

            if nsfw_enabled:
                return await func(client, message, *args, **kwargs)
            else:
                log.warning(
                    "NSFW command blocked by guard",
                    func_name=func.__name__,
                    chat_id=message.chat.id,
                )
                await message.reply_text(
                    "🔞 Эта команда отключена, так как NSFW-контент запрещен в этом чате.\n"
                    "Администратор может включить его с помощью команды `/config enable nsfw`."
                )
                return

        except Exception:
            log.exception(
                "Failed to check NSFW guard, blocking command as a precaution",
                func_name=func.__name__,
            )
            await message.reply_text(
                "❌ Не удалось проверить настройки чата. Пожалуйста, попробуйте позже."
            )
            return

    return wrapper
