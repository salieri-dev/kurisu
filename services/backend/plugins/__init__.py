"""Plugin system for autodiscovery and dynamic route registration."""

import importlib
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from structlog import get_logger

logger = get_logger(__name__)


class PluginBase:
    """Base class for plugins to ensure consistent interface."""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.router: APIRouter | None = None
        self.metadata: dict[str, Any] = {}

    def get_router(self) -> APIRouter | None:
        """Get the plugin's router. Should be implemented by subclasses."""
        return self.router

    def get_metadata(self) -> dict[str, Any]:
        """Get plugin metadata."""

        default_metadata = {"name": self.name, "version": self.version}
        default_metadata.update(self.metadata)
        return default_metadata


class PluginDiscovery:
    """Handles automatic discovery and registration of plugins."""

    def __init__(
        self, plugins_dir: str = "plugins", excluded_plugins: list[str] | None = None
    ):
        self.plugins_dir = (
            Path(__file__).parent if plugins_dir == "plugins" else Path(plugins_dir)
        )
        self.excluded_plugins = set(excluded_plugins or [])
        self.discovered_plugins: dict[str, PluginBase] = {}

    def discover_plugins(self) -> dict[str, PluginBase]:
        """Discover all valid plugins in the plugins directory."""
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory {self.plugins_dir} does not exist")
            return {}

        for endpoint_file in self.plugins_dir.rglob("**/endpoint.py"):
            plugin_path = endpoint_file.parent

            if (plugin_path / "endpoint.py").exists():
                relative_path = plugin_path.relative_to(self.plugins_dir)
                plugin_name = str(relative_path).replace(os.sep, "/")

                if plugin_name in self.excluded_plugins:
                    logger.info(f"Skipping excluded plugin: {plugin_name}")
                    continue

                if any(part.startswith("_") for part in relative_path.parts):
                    continue

                plugin = self._load_plugin(plugin_path, plugin_name)
                if plugin:
                    self.discovered_plugins[plugin_name] = plugin

        return self.discovered_plugins

    def _load_plugin(self, plugin_path: Path, plugin_name: str) -> PluginBase | None:
        """Load a single plugin from its directory."""

        endpoint_file = plugin_path / "endpoint.py"
        if not endpoint_file.exists():
            logger.warning(f"No endpoint.py found for plugin {plugin_name}")
            return None

        module_name = plugin_name.replace("/", ".")
        module_path = f"plugins.{module_name}.endpoint"
        module = importlib.import_module(module_path)

        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            logger.warning(f"No valid router found in {plugin_name}/endpoint.py")
            return None

        plugin = PluginBase(plugin_name)
        plugin.router = router
        plugin.metadata = {}

        init_file = plugin_path / "__init__.py"
        if init_file.exists():
            module_name = plugin_name.replace("/", ".")
            init_module_path = f"plugins.{module_name}"
            init_module = importlib.import_module(init_module_path)
            if hasattr(init_module, "PLUGIN_METADATA"):
                plugin.metadata = getattr(init_module, "PLUGIN_METADATA", {})
                plugin.version = plugin.metadata.get("version", plugin.version)

        return plugin

    def register_plugins(self, app) -> None:
        """Register all discovered plugins with the FastAPI app."""
        for plugin_name, plugin in self.discovered_plugins.items():
            router = plugin.get_router()
            if router:
                app.include_router(
                    router, prefix=f"/{plugin_name}", tags=[plugin_name.title()]
                )
                logger.info(f"Registered plugin routes for {plugin_name}")
            else:
                logger.warning(f"No router to register for plugin {plugin_name}")


plugin_discovery = PluginDiscovery()


def init_plugins(app, excluded_plugins: list[str] | None = None) -> None:
    """Initialize plugin system and register all discovered plugins."""
    global plugin_discovery

    if excluded_plugins:
        plugin_discovery = PluginDiscovery(excluded_plugins=excluded_plugins)

    plugins = plugin_discovery.discover_plugins()

    plugin_discovery.register_plugins(app)

    logger.info(f"Plugin system initialized. Found {len(plugins)} plugins.")
