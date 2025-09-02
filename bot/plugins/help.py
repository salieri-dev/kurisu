import structlog
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.chat_config import get_chat_config
from utils.help_registry import command_help

log = structlog.get_logger(__name__)


@Client.on_message(filters.command("help"), group=1)
async def help_command(client: Client, message: Message):
    """Shows available commands, dynamically grouped by category."""
    try:
        # The complex, duplicated logic is now replaced by a single, clean call
        # to the universal chat configuration utility.
        nsfw_allowed = await get_chat_config(
            message, key="nsfw_enabled", default=False
        )

        # Group commands by their handler definition to avoid showing duplicate descriptions
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

        # Group the processed handlers by their category for display
        grouped_handlers: dict[str, list[dict]] = {}
        for handler in handlers.values():
            group = handler["group"]
            # Skip NSFW commands if not allowed in this chat
            if group == "NSFW" and not nsfw_allowed:
                continue

            if group not in grouped_handlers:
                grouped_handlers[group] = []
            handler["commands"].sort()
            grouped_handlers[group].append(handler)

        # Build the final help message string
        help_text = ["**Доступные команды:**"]
        
        # Sort groups to ensure a consistent order, keeping NSFW at the end
        sorted_groups = sorted(
            grouped_handlers.items(), key=lambda item: item[0] == "NSFW"
        )

        for group, h_list in sorted_groups:
            emoji = group_emojis.get(group, "🔹")
            help_text.append(f"\n{emoji} **{group}**")

            # Sort commands within each group alphabetically
            for handler in sorted(h_list, key=lambda x: x["commands"][0]):
                cmds = ", ".join(f"`/{cmd}`" for cmd in handler["commands"])
                args = f" {handler['arguments']}" if handler['arguments'] else ""
                description = handler["description"]
                help_text.append(f"• {cmds}{args} — {description}")

        # Add a section for features that don't have explicit commands
        help_text.extend(
            [
                "\n**Пассивный функционал:**",
                "• Скачивает посты из Instagram по ссылке.",
                "\n> Бот находится в активной разработке. По вопросам и предложениям: @not_salieri",
            ]
        )

        # If NSFW commands were hidden, add a note explaining how to enable them
        if not nsfw_allowed:
            help_text.append(
                "\n> 🔞 Некоторые команды скрыты. Чтобы их увидеть, администратор должен включить NSFW-режим: `/config enable nsfw`"
            )

        await message.reply_text(
            "\n".join(help_text), quote=True, disable_web_page_preview=True
        )

    except Exception:
        # Use the standardized exception logging for any unexpected errors
        log.exception("An unhandled error occurred in /help command")
        await message.reply_text(
            "❌ Произошла ошибка при формировании списка команд.", quote=True
        )