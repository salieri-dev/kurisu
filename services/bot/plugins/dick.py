import base64
import io
from typing import Any
import structlog
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import handle_api_errors, nsfw_guard, rate_limit
from utils.help_registry import command_handler

log = structlog.get_logger(__name__)


def get_size_category(length: float) -> str:
    """Determines the size category based on erect length."""
    if length < 13:
        return "Ниже среднего"
    if length < 14.9:
        return "Чуть ниже среднего"
    if length < 17.1:
        return "Средний"
    if length < 19:
        return "Выше среднего"
    return "Значительно выше среднего"


def get_satisfaction_comment(rating: float) -> str:
    """Determines the satisfaction comment based on the rating percentage."""
    if rating < 20:
        return "Сложно удовлетворить"
    if rating < 40:
        return "Ниже среднего"
    if rating < 61:
        return "Средний уровень удовлетворения"
    if rating < 80:
        return "Выше среднего, хорошие шансы"
    return "Отличные шансы на удовлетворение"


def format_measurement(value: float) -> str:
    return f'{value:.2f} см ({value / 2.54:.2f}")'


def get_rigidity_level(rigidity: float) -> str:
    return (
        "🥔 Мягкий"
        if rigidity < 30
        else "🥕 Средний"
        if rigidity < 70
        else "🍆 Стальной"
    )


def get_curvature_description(curvature: float) -> str:
    return (
        "⬆️ Прямой"
        if abs(curvature) < 10
        else "↗️ Небольшой изгиб"
        if abs(curvature) < 20
        else "➰ Значительный изгиб"
    )


def get_velocity_description(velocity: float) -> str:
    return (
        "🐌 Слабая" if velocity < 10 else "🚀 Сильная" if velocity < 20 else "☄️ Убьёт"
    )


def get_stamina_description(stamina: float) -> str:
    return (
        "⚡ Скорострел"
        if stamina < 10
        else "🏃‍♂️ Марафонец"
        if stamina > 30
        else "⏱️ Средний"
    )


def get_refractory_description(refractory_period: float) -> str:
    return (
        "🔄 Готов когда-угодно!"
        if refractory_period < 15
        else "😴 Нужен перерыв"
        if refractory_period > 60
        else "🔂 Можешь несколько раз"
    )


def get_sensitivity_description(sensitivity: float) -> str:
    return (
        "🗿 Чувствую, как камень"
        if sensitivity < 3
        else "🎭 Сверхчувствительный"
        if sensitivity > 8
        else "😌 Комфортное"
    )


def create_report(attributes: dict[str, Any], name: str) -> str:
    """Generates the formatted report text using raw data from the API."""
    size_category = get_size_category(attributes["length_erect"])
    satisfaction_comment = get_satisfaction_comment(attributes["satisfaction_rating"])
    report = f"""🍆 **Пенис {name}** 🍆
📏 **Размеры**
  ├─ В эрекции:
  │  ├─ Длина: {format_measurement(attributes["length_erect"])}
  │  ├─ Обхват: {format_measurement(attributes["girth_erect"])}
  │  └─ Объём: {attributes["volume_erect"]:.2f} см³
  │
  └─ В покое:
     ├─ Длина: {format_measurement(attributes["length_flaccid"])}
     ├─ Обхват: {format_measurement(attributes["girth_flaccid"])}
     └─ Объём: {attributes["volume_flaccid"]:.2f} см³
🦸‍♂️ **Суперсилы**
  ├─ 💪 Твёрдость: {get_rigidity_level(attributes["rigidity"])} ({attributes["rigidity"]:.2f}%)
  ├─ ↪️ Кривизна: {get_curvature_description(attributes["curvature"])} ({attributes["curvature"]:.2f}°)
  ├─ 🚀 Скорость: {get_velocity_description(attributes["velocity"])} ({attributes["velocity"]:.2f} км/ч)
  ├─ ⏱️ Выносливость: {get_stamina_description(attributes["stamina"])} ({attributes["stamina"]:.2f} мин)
  ├─ 🔄 Восстановление: {get_refractory_description(attributes["refractory_period"])} ({attributes["refractory_period"]:.2f} мин)
  └─ 🎭 Чувствительность: {get_sensitivity_description(attributes["sensitivity"])} ({attributes["sensitivity"]:.2f}/10)
📊 **Статистика**
  ├─ 📏 Категория размера: {size_category}
  └─ 😍 Рейтинг удовлетворения: {attributes["satisfaction_rating"]:.2f}%
     └─ 💬 {satisfaction_comment}
"""
    return report


@Client.on_message(filters.command("dick"), group=1)
@command_handler(commands=["dick"], description="Измеряет твой пенис.", group="NSFW")
@nsfw_guard
@rate_limit(
    config_key_prefix="fun/dick.rate_limit",
    default_seconds=5,
    default_limit=1,
    key="user",
    silent=False,
)
@handle_api_errors
async def handle_dick(client: Client, message: Message):
    """Handle /dick command."""
    wait_msg = await message.reply_text("🍆 Измеряю...", quote=True)
    message.wait_msg = wait_msg
    attributes_data = await backend_client.get("/fun/dick/generate", message=message)
    name = message.from_user.username or message.from_user.first_name
    report_text = create_report(attributes_data, name=name)
    image_response = await backend_client.post(
        "/fun/dick/image", message=message, json=attributes_data
    )
    image_base64 = image_response.get("image_base64")
    if image_base64:
        image_bytes = base64.b64decode(image_base64)
        await message.reply_photo(photo=io.BytesIO(image_bytes), caption=report_text)
    else:
        await message.reply_text(report_text)
    await wait_msg.delete()
