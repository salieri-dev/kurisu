import os
import asyncio
import structlog
from config import credentials
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from pyrogram.client import Client
from pyrogram.sync import idle
from jobs.manager import init_scheduled_jobs
from kurisu_core.logging_config import setup_structlog
from kurisu_core.tracing import setup_tracing

logger = structlog.get_logger(__name__)


async def main():
    """Main asynchronous bot function."""
    setup_structlog(json_logs=os.getenv("JSON_LOGS", "false").lower() == "true")
    setup_tracing(service_name=os.getenv("SERVICE_NAME", "bot"))
    HTTPXClientInstrumentor().instrument()

    app = Client(
        credentials.bot.name,
        api_id=credentials.bot.app_id,
        api_hash=credentials.bot.api_hash,
        bot_token=credentials.bot.bot_token,
        plugins=dict(root="plugins"),
    )

    async with app:
        logger.info("Client connected. Initializing scheduled jobs...")
        init_scheduled_jobs(app)
        logger.info(
            f"Bot '{credentials.bot.name}' started successfully. Waiting for updates..."
        )
        await idle()

    logger.info("Bot shutting down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error("A critical error occurred.", error=str(e), exc_info=True)
