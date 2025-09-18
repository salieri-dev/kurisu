import importlib
from pathlib import Path
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorDatabase
from structlog import get_logger

logger = get_logger(__name__)


async def init_plugins(app: FastAPI, db: AsyncIOMotorDatabase):
    """
    Discover, load, and set up all plugins.
    """
    plugins_dir = Path(__file__).parent
    for plugin_file in plugins_dir.rglob("**/plugin.py"):
        # Construct module path like 'plugins.core.chat_config.plugin'
        relative_path = plugin_file.relative_to(plugins_dir.parent)
        module_path = ".".join(relative_path.parts).removesuffix(".py")

        try:
            module = importlib.import_module(module_path)
            # Find the first class in the file that looks like our plugin class
            for item in dir(module):
                plugin_class = getattr(module, item)
                if isinstance(plugin_class, type) and hasattr(plugin_class, "setup"):
                    plugin_instance = plugin_class()
                    logger.info(f"Setting up plugin: {plugin_instance.name}")
                    await plugin_instance.setup(app, db)
                    break  # Found and setup the plugin, move to the next file
        except Exception as e:
            logger.error(
                f"Failed to load plugin from {module_path}", error=e, exc_info=True
            )
