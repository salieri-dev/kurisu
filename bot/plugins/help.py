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
        nsfw_allowed = await get_chat_config(message, key="nsfw_enabled", default=False)

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

        grouped_handlers: dict[str, list[dict]] = {}
        for handler in handlers.values():
            group = handler["group"]

            if group == "NSFW" and not nsfw_allowed:
                continue

            if group not in grouped_handlers:
                grouped_handlers[group] = []
            handler["commands"].sort()
            grouped_handlers[group].append(handler)

        help_text = ["**Доступные команды:**"]

        sorted_groups = sorted(
            grouped_handlers.items(), key=lambda item: item[0] == "NSFW"
        )

        for group, h_list in sorted_groups:
            emoji = group_emojis.get(group, "🔹")
            help_text.append(f"\n{emoji} **{group}**")

            for handler in sorted(h_list, key=lambda x: x["commands"][0]):
                cmds = ", ".join(f"`/{cmd}`" for cmd in handler["commands"])
                args = f" {handler['arguments']}" if handler["arguments"] else ""
                description = handler["description"]
                help_text.append(f"• {cmds}{args} — {description}")

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

    except Exception:
        log.exception("An unhandled error occurred in /help command")
        await message.reply_text(
            "❌ Произошла ошибка при формировании списка команд.", quote=True
        )
