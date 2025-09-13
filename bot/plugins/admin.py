# path: bot/plugins/admin.py

import json
import shlex
from datetime import datetime, timedelta
import pytz
from pyrogram import Client, filters
from pyrogram.types import Message
from structlog import get_logger

from utils.api_client import backend_client
from utils.decorators import owner_only, handle_api_errors
from utils.message_utils import split_message
from jobs.manager import get_job_manager_instance

log = get_logger(__name__)
MOSCOW_TZ = pytz.timezone("Europe/Moscow")


@Client.on_message(filters.command("stats") & filters.private)
@owner_only
@handle_api_errors
async def stats_command(client: Client, message: Message):
    """
    Fetches and displays comprehensive bot statistics from the backend API.
    This command is restricted to the bot owner.
    """
    wait_msg = await message.reply("📊 Собираю статистику...", quote=True)
    stats = await backend_client.get("/analytics/stats/summary", message=message)

    if not stats:
        await wait_msg.edit_text("❌ Не удалось получить статистику с сервера.")
        return

    report = "📊 **Статистика бота**\n\n"
    report += f"**Всего сообщений:** `{stats.get('total_messages', 'N/A')}`\n"
    report += (
        f"**Уникальных пользователей:** `{stats.get('total_unique_users', 'N/A')}`\n"
    )
    report += f"**Активных за месяц:** `{stats.get('monthly_active_users', 'N/A')}` (команды: `{stats.get('monthly_command_users', 'N/A')}`)\n"
    report += (
        f"**Час пик (МСК):** `{stats.get('most_active_hour_moscow', 'N/A')}:00`\n\n"
    )

    if top_chats := stats.get("top_10_chats"):
        report += "**Топ 10 чатов по сообщениям:**\n"
        for chat in top_chats:
            report += f"- `{chat.get('title') or 'Unknown Chat'}`: {chat.get('message_count', 0)}\n"
        report += "\n"

    if top_users := stats.get("top_10_monthly_active_users"):
        report += "**Топ 10 активных пользователей (месяц):**\n"
        for user in top_users:
            report += f"- `{user.get('display_name') or 'Unknown User'}`: {user.get('message_count', 0)}\n"

    await wait_msg.delete()
    for part in split_message(report):
        await message.reply_text(part, quote=True)


@Client.on_message(filters.command("get_media") & filters.private)
@owner_only
async def get_media_command(client: Client, message: Message):
    """Sends a media file by its file_id for debugging."""
    if len(message.command) < 3:
        await message.reply(
            "Usage: /get_media [type] [file_id]\n\nSupported: photo, video, animation, document, voice"
        )
        return
    media_type, file_id = message.command[1].lower(), message.command[2]
    log.info("get_media requested", media_type=media_type, file_id=file_id)
    try:
        send_method = getattr(client, f"send_{media_type}", None)
        if send_method:
            await send_method(message.chat.id, file_id)
        else:
            await message.reply("Unsupported media type.")
    except Exception as e:
        await message.reply(f"Error sending media: {e}")


@Client.on_message(filters.command("debug") & filters.private)
@owner_only
@handle_api_errors
async def debug_command(client: Client, message: Message):
    """Provides a set of debug commands for the bot owner."""
    if len(message.command) < 2:
        await message.reply_text(
            "**🛠️ Debug Panel**\n\n"
            "**Usage:** `/debug [subcommand] [options]`\n\n"
            "**Subcommands:**\n"
            "• `run_reconciliation` - Manually triggers the daily chat profile job.\n"
            "• `run_summary [chat_id] [today|yesterday]` - Force-generates a summary for a chat.\n"
            "• `event [key=value ...]` - Triggers a test event on the backend.\n\n"
            "**Event Options:**\n"
            "`level`: `info`, `warning`, `error`, `exception`\n"
            '`msg`: `"Your test message"`\n'
            "`code`: `200`, `404`, `500`, etc.\n"
            "`delay`: `0.5`, `2` (seconds)\n"
            "`spans`: `true` or `false`\n\n"
            "**Example:**\n"
            "`/debug run_summary -100123456789 today`\n"
            '`/debug event level=error msg="Test"`'
        )
        return

    subcommand = message.command[1].lower()
    args = message.command[2:]

    if subcommand == "run_reconciliation":
        manager = get_job_manager_instance()
        if not manager:
            await message.reply(
                "❌ **Job manager not found.** The bot might still be initializing."
            )
            return

        reconciliation_job = manager.get_reconciliation_job()
        await message.reply("▶️ **Starting manual reconciliation job...**")
        await reconciliation_job.reconcile_all_chats()
        await message.reply(
            "✅ **Reconciliation job finished.** Check logs for details."
        )

    elif subcommand == "run_summary":
        if len(args) < 2:
            await message.reply(
                "Usage: `/debug run_summary [chat_id] [today|yesterday]`"
            )
            return

        chat_id_str = args[0]
        try:
            # Validate it's an integer-like string, but use the original string/int for Pyrogram
            chat_id = int(chat_id_str)
        except ValueError:
            await message.reply("Invalid Chat ID format.")
            return

        target_day = args[1].lower()
        if target_day == "today":
            date_to_summarize = datetime.now(MOSCOW_TZ)
        elif target_day == "yesterday":
            date_to_summarize = datetime.now(MOSCOW_TZ) - timedelta(days=1)
        else:
            await message.reply("Second argument must be `today` or `yesterday`.")
            return

        wait_msg = await message.reply(
            f"▶️ **Requesting summary for chat `{chat_id}` for `{target_day}`...**"
        )
        message.wait_msg = wait_msg  # For the error decorator

        try:
            target_chat = await client.get_chat(chat_id)

            payload = {
                "chat_id": target_chat.id,  # Use the validated ID from the chat object
                "chat_title": target_chat.title or "Unknown Chat",
                "date": date_to_summarize.strftime("%Y-%m-%d"),
            }
            response = await backend_client.post(
                "/neuro/summary/generate", json=payload, message=message
            )

            await wait_msg.edit_text(
                "✅ **Summary generated. Sending to this chat...**"
            )
            for part in split_message(response["formatted_text"]):
                await message.reply_text(part, disable_web_page_preview=True)
        except Exception as e:
            # The @handle_api_errors decorator will catch APIError and other general exceptions
            # This specific log helps debug if the decorator fails to catch something.
            log.error(
                "Manual summary generation failed inside handler",
                error=str(e),
                exc_info=True,
            )
            await wait_msg.edit_text(
                f"❌ **An unexpected error occurred:**\n`{str(e)}`"
            )

    elif subcommand == "event":
        payload = {
            "log_level": "info",
            "log_message": "This is a test event from the /debug command.",
            "http_status_code": 200,
            "delay_seconds": 0,
            "create_spans": False,
        }
        try:
            args_str = message.text.split(" ", 2)[2] if len(message.command) > 2 else ""
            args_list = shlex.split(args_str)
            for arg in args_list:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    key = key.lower()
                    if key in ["level", "log_level"]:
                        payload["log_level"] = value
                    elif key in ["msg", "message"]:
                        payload["log_message"] = value
                    elif key in ["code", "http_status_code"]:
                        payload["http_status_code"] = int(value)
                    elif key in ["delay"]:
                        payload["delay_seconds"] = float(value)
                    elif key in ["spans"]:
                        payload["create_spans"] = value.lower() in ["true", "1", "yes"]
        except Exception as e:
            await message.reply(f"❌ Invalid argument format: {e}")
            return

        await message.reply(
            f"▶️ Triggering backend event with payload:\n```json\n{json.dumps(payload, indent=2)}\n```"
        )
        await backend_client.post(
            "/utilities/debug/generate", message=message, json=payload
        )
        if payload["http_status_code"] == 200:
            await message.reply(
                "✅ Event triggered successfully (Backend returned HTTP 200 OK)."
            )

    else:
        await message.reply(
            f"Unknown debug subcommand: `{subcommand}`. Use `/debug` for help."
        )
