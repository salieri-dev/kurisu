from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from structlog import get_logger
from utils.api_client import backend_client
from utils.exceptions import APIError

log = get_logger(__name__)

GDPR_CALLBACK_PREFIX = "gdpr_"
CONFIRM_DELETE_CALLBACK = f"{GDPR_CALLBACK_PREFIX}confirm_delete"
CANCEL_DELETE_CALLBACK = f"{GDPR_CALLBACK_PREFIX}cancel_delete"

GENERAL_ERROR = "❌ Произошла ошибка при выполнении команды."


async def call_backend_gdpr_api(message: Message):
    """Call the backend API for GDPR data deletion"""
    try:
        # The backend client handles the correlation ID automatically.
        # We no longer need to generate or pass it here.
        result = await backend_client.request(
            method="DELETE",
            path=f"/core/gdpr/users/{message.from_user.id}",
            message=message,
        )
        return result
    except APIError as e:
        log.error(
            "Backend API error during GDPR deletion",
            correlation_id=e.correlation_id,
            user_id=message.from_user.id,
            status_code=e.status_code,
            detail=e.detail,
        )
        # We return None to signal failure, which the calling function will handle.
        return None
    except Exception as e:
        # Fallback for unexpected non-API errors
        log.error(f"An unexpected error occurred: {e}", user_id=message.from_user.id)
        return None


@Client.on_message(filters.command("gdpr"), group=1)
async def gdpr_command(client: Client, message: Message):
    """
    Handle the /gdpr command to initiate the GDPR data deletion process.
    Shows a confirmation message with buttons to confirm or cancel.
    """
    try:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Подтвердить удаление", callback_data=CONFIRM_DELETE_CALLBACK
                    ),
                    InlineKeyboardButton(
                        "❌ Отмена", callback_data=CANCEL_DELETE_CALLBACK
                    ),
                ]
            ]
        )

        await message.reply(
            "⚠️ **ВНИМАНИЕ!** ⚠️\n\nВы запросили удаление всех ваших сообщений из базы данных бота.\n\n• Это действие **нельзя отменить**\n\nВы уверены, что хотите продолжить?",
            reply_markup=keyboard,
            quote=True,
        )

    except Exception as e:
        log.error(
            "Error handling gdpr command", error=str(e), user_id=message.from_user.id
        )
        await message.reply(
            "❌ Произошла ошибка при обработке запроса на удаление данных.", quote=True
        )


@Client.on_callback_query(filters.regex(f"^{GDPR_CALLBACK_PREFIX}"))
async def handle_gdpr_callback(client: Client, callback_query: CallbackQuery):
    """
    Handle callbacks from GDPR-related inline keyboard buttons.
    """
    try:
        user_id = callback_query.from_user.id

        if (
            callback_query.message.reply_to_message
            and callback_query.message.reply_to_message.from_user.id != user_id
        ):
            await callback_query.answer(
                "Вы не можете использовать эту кнопку, так как не вы инициировали команду.",
                show_alert=True,
            )
            return

        if callback_query.data == CONFIRM_DELETE_CALLBACK:
            await callback_query.edit_message_text(
                "⏳ Удаление ваших сообщений... Пожалуйста, подождите."
            )

            result = await call_backend_gdpr_api(callback_query.message)

            if not result:
                # The detailed error has already been logged by call_backend_gdpr_api.
                # We just show a generic error to the user.
                await callback_query.edit_message_text(GENERAL_ERROR)
                return

            deleted_count = result.get("deleted_count", 0)
            await callback_query.edit_message_text(
                f"✅ **Удаление завершено**\n\nУдалено сообщений: {deleted_count}\n\nВаших сообщений больше нет в боте"
            )

        elif callback_query.data == CANCEL_DELETE_CALLBACK:
            await callback_query.edit_message_text(
                "❌ **Удаление отменено**\n\nВаши сообщения остались без изменений."
            )

        else:
            await callback_query.answer("Неизвестное действие")

    except Exception as e:
        log.error(
            "Error handling GDPR callback",
            error=str(e),
            user_id=callback_query.from_user.id,
        )
        await callback_query.edit_message_text(
            "❌ Произошла ошибка при обработке запроса на удаление данных."
        )
