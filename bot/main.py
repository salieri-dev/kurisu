"""Main bot application with plugin system."""

import os

import structlog
from config import credentials
from pyrogram import Client

from kurisu_core.logging_config import setup_structlog

logger = structlog.get_logger(__name__)


def main():
    """Main bot function."""
    setup_structlog(json_logs=os.getenv("JSON_LOGS", "false").lower() == "true")
    try:
        app = Client(
            credentials.bot.name,
            api_id=credentials.bot.app_id,
            api_hash=credentials.bot.api_hash,
            bot_token=credentials.bot.bot_token,
            plugins=dict(root="plugins"),
        )
        logger.info(f"Starting bot: {credentials.bot.name}")
        app.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Error starting bot", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    main()
