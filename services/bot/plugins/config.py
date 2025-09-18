import structlog
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import Message
from utils.api_client import backend_client
from utils.decorators import bind_context
from utils.help_registry import command_handler
from utils.redis_utils import redis_client

log = structlog.get_logger(__name__)


async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if a user is an administrator or owner in a chat."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
    except Exception:
        return False


async def get_and_reply_with_config(message: Message, prefix: str = "") -> None:
    """Fetches the current chat config, formats it, and replies to the user."""
    try:
        response = await backend_client.get(
            f"/core/chat_config/{message.chat.id}", message=message
        )
        configs = response.get("configs", {})

        nsfw_enabled = configs.get("nsfw_enabled", False)
        transcribe_enabled = configs.get("transcribe_enabled", True)
        summary_enabled = configs.get("summary_enabled", False)
        summary_roast_enabled = configs.get("summary_roast_enabled", True)

        nsfw_status = "✅ Включен" if nsfw_enabled else "❌ Отключен"
        transcribe_status = "✅ Включена" if transcribe_enabled else "❌ Отключена"
        summary_status = "✅ Включена" if summary_enabled else "❌ Отключена"
        roast_status = "✅ Включена" if summary_roast_enabled else "❌ Отключена"

        config_body = f"""⚙️ **Текущие настройки чата**
• **NSFW-контент**: {nsfw_status}
• **Расшифровка ГС**: {transcribe_status}
• **Ежедневные сводки**: {summary_status}
• **Прожарка от бота в сводках**: {roast_status}

**Как изменить настройки:**
Используйте команду в формате `/config <действие> <параметр>`.

**Действия:**
• `enable` - включить
• `disable` - отключить

**Параметры:**
• `nsfw` - разрешает или запрещает NSFW-контент.
• `transcribe` - включает или отключает расшифровку голосовых.
• `summary` - включает или отключает ежедневные сводки.
• `summary_roast` - включает или отключает прожарку в сводках.

**Пример:**
`/config enable summary`"""
        final_message = f"{prefix}\n\n{config_body}" if prefix else config_body
        await message.reply_text(final_message, disable_web_page_preview=True)
    except Exception as e:
        log.error("Failed to get chat config from API", error=str(e), exc_info=True)
        await message.reply_text(
            "Не удалось получить текущие настройки. Пожалуйста, попробуйте позже."
        )


@Client.on_message(filters.command("config"), group=1)
@command_handler(
    commands=["config"],
    description="Управление настройками чата (только для администраторов).",
    group="Администрирование",
    arguments="[enable/disable] [param]",
)
@bind_context
async def handle_config(client: Client, message: Message):
    """Handle the /config command to view or change chat settings."""
    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text("Эта команда работает только в групповых чатах.")
        return
    if not await is_admin(client, message.chat.id, message.from_user.id):
        log.warning("Non-admin user tried to use /config")
        await message.reply_text(
            "Только администраторы могут просматривать и изменять настройки этого чата."
        )
        return

    args = message.text.split()
    if len(args) == 1:
        log.info("Displaying chat config")
        await get_and_reply_with_config(message)
        return

    if len(args) == 3:
        _, action, param_name = args
        action, param_name = action.lower(), param_name.lower()

        supported_params = {
            "nsfw": "nsfw_enabled",
            "transcribe": "transcribe_enabled",
            "summary": "summary_enabled",
            "summary_roast": "summary_roast_enabled",
        }

        if param_name not in supported_params:
            log.warning("Invalid config parameter used", param=param_name)
            await message.reply_text(
                f"Неизвестный параметр: `{param_name}`. Доступные параметры: `nsfw`, `transcribe`, `summary`, `summary_roast`."
            )
            return

        if action not in ["enable", "disable"]:
            log.warning("Invalid config action used", action=action)
            await message.reply_text(
                f"Неизвестное действие: `{action}`. Используйте `enable` или `disable`."
            )
            return

        param_value = action == "enable"
        db_param_name = supported_params[param_name]

        try:
            log.info(
                "Setting chat config",
                param=db_param_name,
                value=param_value,
                chat_id=message.chat.id,
            )
            await backend_client.post(
                "/core/chat_config/set",
                message=message,
                json={
                    "chat_id": message.chat.id,
                    "param_name": db_param_name,
                    "param_value": param_value,
                },
            )

            cache_key = f"chat_config:{message.chat.id}:{db_param_name}"
            await redis_client.set(cache_key, "1" if param_value else "0", ex=300)
            log.info(
                f"Cache updated for {db_param_name}",
                chat_id=message.chat.id,
                new_value=param_value,
            )

            success_prefix = ""
            if param_name == "nsfw":
                success_prefix = f"✅ NSFW-контент теперь **{'разрешен' if param_value else 'запрещен'}**."
            elif param_name == "transcribe":
                success_prefix = f"✅ Расшифровка голосовых сообщений **{'включена' if param_value else 'отключена'}**."
            elif param_name == "summary":
                success_prefix = f"✅ Ежедневные сводки **{'включены' if param_value else 'отключены'}**."
            elif param_name == "summary_roast":
                success_prefix = f"✅ Прожарка в сводках **{'включена' if param_value else 'отключена'}**."

            await get_and_reply_with_config(message, prefix=success_prefix)
        except Exception as e:
            log.error(
                "Failed to set chat config via API",
                param=db_param_name,
                error=str(e),
                exc_info=True,
            )
            await message.reply_text(
                "Произошла ошибка при изменении настроек. Пожалуйста, попробуйте позже."
            )
        return

    await message.reply_text(
        "Неверное использование команды. Отправьте `/config` без аргументов, чтобы увидеть справку."
    )
