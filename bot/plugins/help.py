# bot/plugins/help.py
"""Dynamic help command that builds its output from the central registry."""

import structlog
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message
from utils.api_client import backend_client

# Import the shared help dictionary
from utils.help_registry import command_help
from utils.redis_utils import redis_client

log = structlog.get_logger(__name__)


async def is_nsfw_enabled(message: Message) -> bool:
    """
    Checks if NSFW commands are enabled for the current chat.
    Mirrors the logic in the nsfw_guard decorator for consistency.
    """
    if message.chat.type == ChatType.PRIVATE:
        return True  # NSFW is always "enabled" in DMs

    cache_key = f"chat_config:{message.chat.id}:nsfw_enabled"
    try:
        cached_value = await redis_client.get(cache_key)
        if cached_value is not None:
            return cached_value == "1"
    except Exception as e:
        log.warning("Redis check failed in help command", error=str(e))

    # Cache miss, fall back to API
    try:
        response = await backend_client.get(
            f"/core/chat_config/{message.chat.id}/nsfw_enabled", message=message
        )
        api_value = response.get("param_value", False)
        # Cache the result for next time
        await redis_client.set(cache_key, "1" if api_value else "0", ex=300)
        return bool(api_value)
    except Exception:
        log.error("API call failed in help command, defaulting to NSFW-disabled.")
        return False


@Client.on_message(filters.command("help"), group=1)
async def help_command(client: Client, message: Message):
    """Shows available commands, dynamically grouped by category."""
    try:
        nsfw_allowed = await is_nsfw_enabled(message)

        # Group commands by their handler definition to avoid duplicates
        handlers: dict[str, dict] = {}
        for cmd, info in command_help.items():
            key = f"{info['group']}:{info['description']}"
            if key not in handlers:
                handlers[key] = {
                    "commands": [],
                    "description": info["description"],
                    "arguments": info["arguments"],
                    "group": info["group"],
                }
            handlers[key]["commands"].append(cmd)

        group_emojis = {
            "Нейронки": "🧠",
            "Рандом": "🎲",
            "Развлечения": "🎉",
            "Утилиты": "🛠️",
            "Администрирование": "⚙️",
            "NSFW": "🔞",
        }

        # Group handlers by category
        grouped_handlers: dict[str, list[dict]] = {}
        for handler in handlers.values():
            group = handler["group"]
            if group == "NSFW" and not nsfw_allowed:
                continue  # Skip NSFW commands if not allowed in this chat

            if group not in grouped_handlers:
                grouped_handlers[group] = []
            handler["commands"].sort()
            grouped_handlers[group].append(handler)

        # Build the help message
        help_text = ["**Доступные команды:**"]
        sorted_groups = sorted(
            grouped_handlers.items(), key=lambda item: item[0] != "NSFW"
        )

        for group, h_list in sorted_groups:
            emoji = group_emojis.get(group, "🔹")
            help_text.append(f"\n{emoji} **{group}**")

            for handler in sorted(h_list, key=lambda x: x["commands"][0]):
                cmds = ", ".join(f"`/{cmd}`" for cmd in handler["commands"])
                args = f" {handler['arguments']}" if handler["arguments"] else ""
                description = handler["description"]
                help_text.append(f"• {cmds}{args} — {description}")

        # Add passive functionality section
        help_text.extend(
            [
                "\n**Пассивный функционал:**",
                "• Скачивает посты из Instagram по ссылке.",
                "\n> Бот находится в активной разработке. По вопросам и предложениям: @not_salieri",
            ]
        )

        if not nsfw_allowed:
            help_text.append(
                "\n> 🔞 Некоторые команды скрыты. Чтобы их увидеть, администратор должен включить NSFW-режим: `/config enable nsfw`"
            )

        await message.reply_text(
            "\n".join(help_text), quote=True, disable_web_page_preview=True
        )

    except Exception as e:
        log.error("Error in /help command", error=str(e), exc_info=True)
        await message.reply_text(
            "❌ Произошла ошибка при формировании списка команд.", quote=True
        )
