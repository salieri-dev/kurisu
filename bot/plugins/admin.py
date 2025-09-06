import asyncio
import json
import shlex
from pyrogram import Client, filters
from pyrogram.types import Message
from structlog import get_logger

from utils.api_client import backend_client
from utils.decorators import owner_only, handle_api_errors
from utils.message_utils import split_message
from jobs.active_chats import get_job_instance

log = get_logger(__name__)


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

    report = f"📊 **Статистика бота**\n\n"
    report += f"**Всего сообщений:** `{stats['total_messages']}`\n"
    report += f"**Уникальных пользователей:** `{stats['total_unique_users']}`\n"
    report += f"**Активных за месяц:** `{stats['monthly_active_users']}` (команды: `{stats['monthly_command_users']}`)\n"
    report += f"**Час пик (МСК):** `{stats.get('most_active_hour_moscow', 'N/A')}:00`\n\n"

    if stats.get('top_10_chats'):
        report += "**Топ 10 чатов по сообщениям:**\n"
        for chat in stats['top_10_chats']:
            report += f"- `{chat.get('title') or 'Unknown Chat'}`: {chat['message_count']}\n"
        report += "\n"

    if stats.get('top_10_monthly_active_users'):
        report += "**Топ 10 активных пользователей (месяц):**\n"
        for user in stats['top_10_monthly_active_users']:
            report += f"- `{user.get('display_name') or 'Unknown User'}`: {user['message_count']}\n"
    
    await wait_msg.delete()
    for part in split_message(report):
        await message.reply_text(part, quote=True)


@Client.on_message(filters.command("get_media") & filters.private)
@owner_only
async def get_media_command(client: Client, message: Message):
    """
    Sends a media file by its file_id for debugging.
    """
    if len(message.command) < 3:
        await message.reply("Usage: /get_media [type] [file_id]\n\nSupported: photo, video, animation, document, voice")
        return
    
    media_type, file_id = message.command[1].lower(), message.command[2]
    log.info(f"get_media requested", media_type=media_type, file_id=file_id)

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
    """
    Provides a set of debug commands for the bot owner.
    """
    if len(message.command) < 2:
        await message.reply_text(
            "**🛠️ Debug Panel**\n\n"
            "**Usage:** `/debug [subcommand] [options]`\n\n"
            "**Subcommands:**\n"
            "• `run_reconciliation` - Manually triggers the daily chat profile job.\n"
            "• `event [key=value ...]` - Triggers a test event on the backend.\n\n"
            "**Event Options:**\n"
            "`level`: `info`, `warning`, `error`, `exception`\n"
            "`msg`: `\"Your test message\"`\n"
            "`code`: `200`, `404`, `500`, etc.\n"
            "`delay`: `0.5`, `2` (seconds)\n"
            "`spans`: `true` or `false`\n\n"
            "**Example:**\n"
            "`/debug event level=error code=503 msg=\"Simulate backend failure\"`"
        )
        return

    subcommand = message.command[1].lower()

    if subcommand == "run_reconciliation":
        job_instance = get_job_instance()
        if not job_instance:
            await message.reply("❌ **Job instance not found.** The bot might still be initializing.")
            return

        await message.reply("▶️ **Starting manual reconciliation job...**")
        task = asyncio.create_task(job_instance.reconcile_all_chats())
        await task
        await message.reply("✅ **Reconciliation job finished.** Check logs for details.")

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
            args = shlex.split(args_str)
            for arg in args:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    key = key.lower()
                    if key in ["level", "log_level"]: payload["log_level"] = value
                    elif key in ["msg", "message"]: payload["log_message"] = value
                    elif key in ["code", "http_status_code"]: payload["http_status_code"] = int(value)
                    elif key in ["delay"]: payload["delay_seconds"] = float(value)
                    elif key in ["spans"]: payload["create_spans"] = value.lower() in ["true", "1", "yes"]
        except Exception as e:
            await message.reply(f"❌ Invalid argument format: {e}")
            return

        await message.reply(f"▶️ Triggering backend event with payload:\n```json\n{json.dumps(payload, indent=2)}\n```")
        
        await backend_client.post("/utilities/debug/generate", message=message, json=payload)
        
        if payload["http_status_code"] == 200:
            await message.reply("✅ Event triggered successfully (Backend returned HTTP 200 OK).")

    else:
        await message.reply(f"Unknown debug subcommand: `{subcommand}`. Use `/debug` for help.")