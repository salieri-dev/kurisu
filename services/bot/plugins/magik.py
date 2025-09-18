from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message
from structlog import get_logger
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit
from utils.help_registry import command_handler
from utils.media_helpers import get_media_as_bytes

log = get_logger(__name__)
ERROR_NO_MEDIA = "Пожалуйста, ответьте на сообщение с изображением/GIF или отправьте его вместе с командой."


async def process_image_command(
    message: Message,
    endpoint: str,
    base_filename: str,
    data: dict | None = None,
):
    """
    Generic handler for processing an image via a backend endpoint.
    Lets the @handle_api_errors decorator manage all exceptions.
    """
    wait_msg = await message.reply_text("✨ Обрабатываю изображение...", quote=True)
    message.wait_msg = wait_msg
    media_data = await get_media_as_bytes(message)
    if not media_data:
        await wait_msg.edit_text(ERROR_NO_MEDIA)
        return
    media_bytes, is_input_gif = media_data
    file_name = "animation.gif" if is_input_gif else "image.png"
    file_mime = "image/gif" if is_input_gif else "image/png"
    result_bytes, result_mime_type = await backend_client.post_media(
        endpoint,
        message=message,
        file_bytes=media_bytes,
        file_name=file_name,
        file_mime=file_mime,
        data=data,
    )
    output = BytesIO(result_bytes)
    if "gif" in result_mime_type:
        output.name = f"{base_filename}.gif"
        await message.reply_animation(animation=output, quote=True)
    else:
        output.name = f"{base_filename}.png"
        await message.reply_photo(photo=output, quote=True)
    await wait_msg.delete()


@Client.on_message(filters.command("magik"), group=1)
@command_handler(
    commands=["magik"],
    description="Применяет магическое искажение к изображению.",
    group="Развлечения",
)
@rate_limit("fun/magik.rate_limit", default_seconds=10, default_limit=1)
@nsfw_guard
@handle_api_errors
async def magik_cmd(client: Client, message: Message):
    await process_image_command(message, "/fun/magik/magik", "magik")


@Client.on_message(filters.command("pixel"), group=1)
@command_handler(
    commands=["pixel"],
    description="Пикселизирует изображение.",
    group="Развлечения",
)
@rate_limit("fun/magik.rate_limit", default_seconds=10, default_limit=1)
@nsfw_guard
@handle_api_errors
async def pixel_cmd(client: Client, message: Message):
    await process_image_command(message, "/fun/magik/pixel", "pixel")


@Client.on_message(filters.command(["waaw", "haah", "woow", "hooh"]), group=1)
@command_handler(
    commands=["waaw", "haah", "woow", "hooh"],
    description="Применяет различные эффекты зеркалирования.",
    group="Развлечения",
)
@rate_limit("fun/magik.rate_limit", default_seconds=10, default_limit=1)
@nsfw_guard
@handle_api_errors
async def mirror_cmd(client: Client, message: Message):
    effect = message.command[0].lower()
    await process_image_command(message, f"/fun/magik/mirror/{effect}", effect)


@Client.on_message(filters.command(["flip", "flop", "invert"]), group=1)
@command_handler(
    commands=["flip", "flop", "invert"],
    description="Простые трансформации: переворот, отражение, инверсия.",
    group="Развлечения",
)
@rate_limit("fun/magik.rate_limit", default_seconds=10, default_limit=1)
@nsfw_guard
@handle_api_errors
async def transform_cmd(client: Client, message: Message):
    transform_type = message.command[0].lower()
    await process_image_command(
        message, f"/fun/magik/transform/{transform_type}", transform_type
    )


@Client.on_message(filters.command("rotate"), group=1)
@command_handler(
    commands=["rotate"],
    description="Поворачивает изображение.",
    group="Развлечения",
    arguments="[градусы]",
)
@rate_limit("fun/magik.rate_limit", default_seconds=10, default_limit=1)
@nsfw_guard
@handle_api_errors
async def rotate_cmd(client: Client, message: Message):
    degrees = 90
    if len(message.command) > 1:
        try:
            degrees = int(message.command[1])
        except ValueError:
            pass
    await process_image_command(
        message, "/fun/magik/rotate", "rotated", data={"degrees": degrees}
    )
