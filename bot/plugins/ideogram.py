import structlog
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, rate_limit
from utils.help_registry import command_handler

log = structlog.get_logger(__name__)


@Client.on_message(filters.command("ideogram"), group=1)
@command_handler(
    commands=["ideogram"],
    description="Генерирует 4 изображения по текстовому описанию.",
    group="Нейронки",
    arguments="[промпт]",
)
@rate_limit(
    config_key_prefix="neuro/ideogram.rate_limit",
    default_seconds=90,
    default_limit=2,
    key="user",
)
@handle_api_errors
async def ideogram_command(client: Client, message: Message):
    """Handles the /ideogram command by calling the backend service."""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Пожалуйста, укажите промпт: `/ideogram [текст]`", quote=True
        )
        return

    prompt = message.text.split(maxsplit=1)[1]

    wait_msg = await message.reply_text("🎨 Генерирую изображения...", quote=True)
    message.wait_msg = wait_msg

    response = await backend_client.post(
        "/neuro/ideogram/generate", message=message, json={"prompt": prompt}
    )

    image_urls = response.get("image_urls", [])
    if not image_urls:
        await wait_msg.edit_text(
            "❌ Не удалось сгенерировать изображения. Попробуйте другой промпт."
        )
        return

    seed = response.get("seed", "N/A")
    caption = f"🎨 **Промпт:** `{prompt}`\n🌱 **Seed:** `{seed}`"

    media_group = []
    for i, url in enumerate(image_urls):
        media_group.append(
            InputMediaPhoto(media=url, caption=caption if i == 0 else None)
        )

    await message.reply_media_group(media=media_group, quote=True)
    await wait_msg.delete()
