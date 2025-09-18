"""Random plugin for bot that communicates with backend API."""

import structlog
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors
from utils.help_registry import command_handler

log = structlog.get_logger(__name__)


@Client.on_message(filters.command("choice"), group=1)
@command_handler(
    commands=["choice"],
    description="Выбирает случайный вариант из предложенных.",
    group="Рандом",
    arguments="[вариант1;вариант2;...]",
)
@handle_api_errors
async def handle_choice(client: Client, message: Message):
    """Handle /choice command."""

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /choice вариант1;вариант2;вариант3")
        return

    options = args[1].strip()
    if not options:
        await message.reply(
            "Пожалуйста, укажите варианты, разделенные точкой с запятой."
        )
        return

    result = await backend_client.get(
        "/fun/random/choice", message=message, params={"options": options}
    )

    await message.reply(f"🎲 {result['choice']}")


@Client.on_message(filters.command("roll"), group=1)
@command_handler(
    commands=["roll"], description="Бросает шестигранный кубик.", group="Рандом"
)
@handle_api_errors
async def handle_roll(client: Client, message: Message):
    """Handle /roll command."""
    result = await backend_client.get("/fun/random/roll", message=message)
    await message.reply(f"🎲 {result['result']}")


@Client.on_message(filters.command("flip"), group=1)
@command_handler(commands=["flip"], description="Подбрасывает монетку.", group="Рандом")
@handle_api_errors
async def handle_flip(client: Client, message: Message):
    """Handle /flip command."""
    result = await backend_client.get("/fun/random/flip", message=message)
    await message.reply(f"🪙 {result['result']}")


@Client.on_message(filters.command("8ball"), group=1)
@command_handler(
    commands=["8ball"],
    description="Даёт предсказание от магического шара.",
    group="Рандом",
)
@handle_api_errors
async def handle_8ball(client: Client, message: Message):
    """Handle /8ball command."""
    result = await backend_client.get("/fun/random/8ball", message=message)
    await message.reply(f"🔮 {result['prediction']}")


@Client.on_message(filters.command("random"), group=1)
@command_handler(
    commands=["random"],
    description="Генерирует случайное число в диапазоне.",
    group="Рандом",
    arguments="[min] [max]",
)
@handle_api_errors
async def handle_random(client: Client, message: Message):
    """Handle /random command."""
    args = message.text.split()
    min_val, max_val = 1, 100

    if len(args) >= 2:
        try:
            min_val = int(args[1])
        except ValueError:
            min_val = 1
    if len(args) >= 3:
        try:
            max_val = int(args[2])
        except ValueError:
            max_val = 100

    if min_val >= max_val:
        await message.reply("Минимальное значение должно быть меньше максимального.")
        return

    result = await backend_client.get(
        "/fun/random/number",
        message=message,
        params={"min_value": min_val, "max_value": max_val},
    )
    await message.reply(f"🎲 {result['result']} (от {min_val} до {max_val})")
