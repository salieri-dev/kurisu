"""Altgirls plugin for Pyrogram: requests backend API and sends album with funny captions."""

import base64
import io
import random

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import ChatMember, InputMediaPhoto, Message
from structlog import get_logger
from utils.api_client import backend_client
from utils.decorators import nsfw_guard, rate_limit

log = get_logger(__name__)

NO_IMAGES_FOUND = "Изображения не найдены."
GENERAL_ERROR = "❌ Произошла ошибка! Попробуйте позже."

RELATIONSHIP_TERMS = [
    "жена",
    "девушка",
    "любовница",
    "питомец",
    "сестра",
    "мама",
    "тёща",
    "ебнёт камнем",
    "изобьёт",
    "наступит на яйца",
    "оторвёт яйца",
    "покажет ножки",
    "задушит",
    "убьет",
    "фемверсия",
    "трапик",
    "приготовит хачапури",
    "сохнет по",
    "изменит",
    "даст никелевую камушку",
    "послушает музыку",
    "ненавидит",
    "любит",
    "будет подразнивать",
    "помурлычит в дискордике",
    "подарит цветы",
    "накормит борщом",
    "заставит мыть посуду",
    "познакомит с мамой",
    "напишет стихи",
    "отведет в кино",
    "сделает массаж",
    "испечет пирожки",
    "погладит по голове",
    "споет колыбельную",
    "научит готовить",
    "будет ревновать",
    "постирает носки",
    "заставит носить платье",
    "накрасит губы",
    "сделает прическу",
    "научит танцевать",
    "возьмет на шопинг",
    "будет пилить",
]

ACCUSATIVE_VERBS = [
    "жена",
    "девушка",
    "любовница",
    "питомец",
    "сестра",
    "мама",
    "тёща",
    "ебнёт камнем",
    "разорвёт",
    "насадит на кол",
    "зарежет",
    "засталкерит",
    "женская версия",
    "выебет",
    "задушит",
    "убьет",
    "изобьёт",
    "оторвёт яйца",
    "будет подразнивать",
    "трапик",
    "ненавидит",
    "послушает музыку",
    "любит",
    "изничтожит пенис",
    "закуколдит",
    "посадит в тюрьму",
    "убаюкает перед сном",
    "фемверсия",
    "возьмет замуж",
    "сделает феминистом",
    "заставит готовить",
    "отправит мыть посуду",
    "накрасит губы",
    "оденет в платье",
    "научит вышивать",
    "отведет к маме",
    "заставит смотреть мелодрамы",
    "будет пилить",
    "заставит ходить по магазинам",
    "научит гладить",
    "заставит убираться",
    "научит стирать",
    "сделает домохозяйкой",
    "превратит в подкаблучника",
    "украдет носки",
    "спрячет права",
    "заберет зарплату",
    "заставит спать на диване",
    "возьмет в ЗАГС",
]


async def get_chat_members(client: Client, chat_id: int) -> list[ChatMember]:
    """Get list of chat members excluding bots."""
    try:
        return [
            member
            async for member in client.get_chat_members(chat_id)
            if not member.user.is_bot
        ]
    except Exception:
        return []


def format_source_link(source_link: str) -> str:
    """Formats the source link into a clickable markdown link."""

    if "://" in source_link:
        if "vk.com/" in source_link:
            username = source_link.split("vk.com/")[1].split("/")[0]
            if username:
                return f"[{username}]({source_link})"
        elif "t.me/" in source_link:
            username = source_link.split("t.me/")[1].split("/")[0]
            if username:
                return f"[{username}]({source_link})"
        return source_link

    if "_" not in source_link:
        return f"Неизвестно (источник: {source_link})"

    platform, username = source_link.split("_", 1)

    if platform == "tg":
        return f"[{username}](https://t.me/{username})"
    elif platform == "vk":
        return f"[{username}](https://vk.com/{username})"
    else:
        return f"Неизвестно (источник: {source_link})"


@Client.on_message(filters.command(["altgirls"]), group=1)
@rate_limit(
    config_key_prefix="fun/altgirls.rate_limit",
    default_seconds=3,
    default_limit=1,
    key="user",
    silent=False,
)
@nsfw_guard
async def handle_altgirls(client: Client, message: Message):
    """Handle /altgirls command: fetch images from backend and send with funny caption."""
    try:
        count = 4

        notification = await message.reply_text(
            "🔍 Запрашиваем альтушек...", quote=True
        )

        result = await backend_client.get(
            "/fun/altgirls",
            message=message,
            params={"n": count},
        )

        images = result.get("images", [])
        if not images:
            await notification.delete()
            await message.reply_text(NO_IMAGES_FOUND, quote=True)
            return

        is_private = message.chat.type == ChatType.PRIVATE
        if not is_private:
            combined_caption = f"Всего изображений получено: {len(images)}\n\n"
            members = await get_chat_members(client, message.chat.id)
            for i, img in enumerate(images, 1):
                source_raw = img.get("source_link", "Неизвестно")
                source = format_source_link(source_raw)

                if members:
                    m = random.choice(members)
                    term = random.choice(RELATIONSHIP_TERMS)
                    verb_suffix = (
                        "пользователя"
                        if any(v in term for v in ACCUSATIVE_VERBS)
                        else "пользователю"
                    )
                    user_name = m.user.first_name or m.user.username or "Пользователь"
                    combined_caption += f"Пикча №{i} - {term} {verb_suffix} {user_name} | Источник: {source}\n"
                else:
                    combined_caption += f"Пикча №{i} | Источник: {source}\n"
        else:
            combined_caption = f"Всего изображений получено: {len(images)}\n\n"
            for i, img in enumerate(images, 1):
                source_raw = img.get("source_link", "Неизвестно")
                source = format_source_link(source_raw)
                combined_caption += f"Пикча №{i} | Источник: {source}\n"

        media_group = []
        for idx, img in enumerate(images):
            try:
                raw = base64.b64decode(img["base64_data"])
                bio = io.BytesIO(raw)

                bio.name = img.get("filename") or f"image_{idx + 1}.jpg"
                if idx == 0:
                    media_group.append(
                        InputMediaPhoto(media=bio, caption=combined_caption)
                    )
                else:
                    media_group.append(InputMediaPhoto(media=bio))
            except Exception as e:
                log.error(f"Failed to prepare image {idx + 1}: {e}")

        if not media_group:
            await notification.delete()
            await message.reply_text(GENERAL_ERROR, quote=True)
            return

        await message.reply_media_group(media=media_group, quote=True)
        await notification.delete()

    except Exception as e:
        log.error(f"Error in /altgirls command: {e}")
        try:
            await message.reply_text(GENERAL_ERROR, quote=True)
        except Exception:
            pass
