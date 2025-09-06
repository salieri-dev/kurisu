import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from structlog import get_logger

from utils.api_client import backend_client
from utils.decorators import owner_only, handle_api_errors
from utils.message_utils import split_message
from jobs.active_chats import get_job_instance  # Import the job instance getter

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

    # The user is authorized by @owner_only, the bot is authorized by API key.
    stats = await backend_client.get("/analytics/stats/summary", message=message)

    report = "📊 **Статистика бота**\n\n"
    report += f"**Всего сообщений:** `{stats['total_messages']}`\n"
    report += f"**Уникальных пользователей:** `{stats['total_unique_users']}`\n"
    report += f"**Активных за месяц:** `{stats['monthly_active_users']}` (команды: `{stats['monthly_command_users']}`)\n"
    report += (
        f"**Час пик (МСК):** `{stats.get('most_active_hour_moscow', 'N/A')}:00`\n\n"
    )

    if stats.get("top_10_chats"):
        report += "**Топ 10 чатов по сообщениям:**\n"
        for chat in stats["top_10_chats"]:
            report += (
                f"- `{chat.get('title') or 'Unknown Chat'}`: {chat['message_count']}\n"
            )
        report += "\n"

    if stats.get("top_10_monthly_active_users"):
        report += "**Топ 10 активных пользователей (месяц):**\n"
        for user in stats["top_10_monthly_active_users"]:
            report += f"- `{user.get('display_name') or 'Unknown User'}`: {user['message_count']}\n"

    await wait_msg.delete()
    for part in split_message(report):
        await message.reply_text(part, quote=True)


@Client.on_message(filters.command("get_media") & filters.private)
@owner_only
async def get_media_command(client: Client, message: Message):
    """
    Sends a media file by its file_id. This is a utility command for debugging
    and is restricted to the bot owner.
    """
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
async def debug_command(client: Client, message: Message):
    """
    Provides a set of debug commands for the bot owner to test functionality.
    """
    if len(message.command) < 2:
        await message.reply_text(
            "**🛠️ Debug Panel**\n\n"
            "**Usage:** `/debug [subcommand]`\n\n"
            "**Subcommands:**\n"
            "• `run_reconciliation` - Manually triggers the daily chat profile reconciliation job."
        )
        return

    subcommand = message.command[1].lower()

    if subcommand == "run_reconciliation":
        job_instance = get_job_instance()
        if not job_instance:
            await message.reply(
                "❌ **Job instance not found.** The bot might still be initializing. Please wait a moment and try again."
            )
            return

        await message.reply(
            "▶️ **Starting manual reconciliation job.**\nThis may take some time depending on the number of chats. I will notify you upon completion."
        )

        try:
            # Run the job's main method as a background task to keep the bot responsive.
            task = asyncio.create_task(job_instance.reconcile_all_chats())

            # Wait for the task to complete to provide final feedback.
            await task

            await message.reply(
                "✅ **Reconciliation job finished successfully.**\nCheck the bot's logs for detailed output."
            )
        except Exception as e:
            log.error(
                "Manual reconciliation job trigger failed", error=str(e), exc_info=True
            )
            await message.reply(
                f"❌ **An unexpected error occurred during the job:**\n`{e}`\nCheck logs for more details."
            )

    else:
        await message.reply(
            f"Unknown debug subcommand: `{subcommand}`. Use `/debug` for help."
        )
