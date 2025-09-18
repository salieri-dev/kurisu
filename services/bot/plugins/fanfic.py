import structlog
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit
from utils.help_registry import command_handler
from utils.message_utils import split_message

log = structlog.get_logger(__name__)


@Client.on_message(filters.command("fanfic"), group=1)
@command_handler(
    commands=["fanfic"],
    description="Напишет короткий фанфик на заданную тему и сгенерирует постер.",
    group="Нейронки",
    arguments="[тема]",
)
@rate_limit("neuro/fanfic.rate_limit", 120, 1, key="user")
@nsfw_guard
@handle_api_errors
async def fanfic_command(client: Client, message: Message):
    """Handles the /fanfic command by calling the backend service."""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Пожалуйста, укажите тему для фанфика: `/fanfic [тема]`", quote=True
        )
        return

    topic = message.text.split(maxsplit=1)[1]
    if len(topic) < 3:
        await message.reply_text(
            "❌ Тема слишком короткая! (минимум 3 символа)", quote=True
        )
        return

    wait_msg = await message.reply_text("⚙️ Генерирую фанфик и постер...", quote=True)

    response = await backend_client.post(
        "/neuro/fanfic/generate", message=message, json={"topic": topic}
    )

    title = response["title"]
    content = response["content"]
    image_url = response["image_url"]

    await wait_msg.delete()

    await message.reply_photo(
        photo=image_url, caption=f"🎨 **{title}**\n\n*Текст фанфика ниже.*", quote=True
    )

    for part in split_message(content):
        await message.reply_text(part, quote=True, disable_web_page_preview=True)
