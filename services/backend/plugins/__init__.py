import importlib
from pathlib import Path
import sys
from typing import List, Type, Dict, Any, TypeVar
import structlog
from fastapi import FastAPI, APIRouter, Request, HTTPException
from pydantic_settings import BaseSettings

logger = structlog.get_logger(__name__)
T = TypeVar("T", bound=BaseSettings)


class PluginManager:
    """
    Handles the discovery, configuration loading, and registration of all plugins.
    It now instantiates and holds the configuration for each plugin.
    """

    def __init__(
        self, plugins_dir: str = "plugins", excluded_plugins: List[str] | None = None
    ):
        self.base_path = Path(__file__).parent.parent
        self.plugins_dir = self.base_path / plugins_dir
        self.excluded_plugins = set(excluded_plugins or [])
        self.discovered_routers: Dict[str, APIRouter] = {}
        self.loaded_configs: Dict[str, BaseSettings] = {}
        self._discovery_has_run = False

    def discover(self):
        """
        Discovers all plugin routers and configuration models.
        Instantiates and loads configuration for each plugin found.
        """
        if self._discovery_has_run:
            logger.debug("Plugin discovery has already run. Skipping.")
            return
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory {self.plugins_dir} does not exist.")
            self._discovery_has_run = True
            return

        logger.info("Starting plugin discovery and config loading...")
        for endpoint_file in self.plugins_dir.rglob("endpoint.py"):
            plugin_path = endpoint_file.parent
            if any(part.startswith(("_", ".")) for part in plugin_path.parts):
                continue

            relative_path = plugin_path.relative_to(self.plugins_dir)
            plugin_name = str(relative_path).replace("\\", "/")
            if plugin_name in self.excluded_plugins:
                logger.info(f"Skipping excluded plugin: {plugin_name}")
                continue

            self._load_plugin_components(plugin_path, plugin_name)

        self._discovery_has_run = True

    def _get_module_path(self, file_path: Path) -> str:
        """Constructs the fully-qualified Python module path."""
        relative_to_root = file_path.relative_to(self.base_path.parent)
        return ".".join(relative_to_root.with_suffix("").parts)

    def _load_plugin_components(self, plugin_path: Path, plugin_name: str):
        """Loads routers and configs from a single plugin directory."""
        endpoint_file = plugin_path / "endpoint.py"
        if endpoint_file.exists():
            module_path = self._get_module_path(endpoint_file)
            router = self._import_attribute(module_path, "router")
            if isinstance(router, APIRouter):
                self.discovered_routers[plugin_name] = router
                logger.debug(f"Discovered router for plugin: {plugin_name}")

        config_file = plugin_path / "config.py"
        if config_file.exists():
            module_path = self._get_module_path(config_file)
            module = self._import_module(module_path)
            if module:
                for item_name in dir(module):
                    obj = getattr(module, item_name)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BaseSettings)
                        and obj is not BaseSettings
                    ):
                        try:
                            config_instance = obj()
                            self.loaded_configs[obj.__name__] = config_instance
                            logger.debug(
                                f"Loaded config '{obj.__name__}' for plugin: {plugin_name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to load configuration for plugin '{plugin_name}' using model '{obj.__name__}'. The service may be misconfigured.",
                                error=str(e),
                                exc_info=True,
                            )

    def get_plugin_config(self, model_class: Type[T]) -> T | None:
        """
        Retrieves a loaded and validated plugin configuration instance by its class type.
        """
        instance = self.loaded_configs.get(model_class.__name__)
        if instance and isinstance(instance, model_class):
            return instance
        return None

    def _import_module(self, module_path: str):
        """Dynamically imports a module using its full path."""
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            logger.error(
                f"Failed to import module '{module_path}'", error=str(e), exc_info=True
            )
            return None

    def _import_attribute(self, module_path: str, attribute_name: str) -> Any:
        """Imports a specific attribute from a module."""
        module = self._import_module(module_path)
        if module:
            return getattr(module, attribute_name, None)
        return None

    def register_routers(self, app: FastAPI):
        """Registers all discovered routers with the FastAPI application."""
        if not self.discovered_routers:
            logger.warning("No plugin routers were discovered to register.")
            return

        for plugin_name, router in sorted(self.discovered_routers.items()):
            prefix = f"/{plugin_name}"
            tags = [plugin_name.replace("/", " ").title()]
            app.include_router(router, prefix=prefix, tags=tags)
            logger.info(
                f"Registered plugin routes for '{plugin_name}' at prefix '{prefix}'"
            )


_plugin_manager_instance: PluginManager | None = None


def get_plugin_manager(excluded_plugins: List[str] | None = None) -> PluginManager:
    """
    Gets a singleton instance of the PluginManager and runs discovery.
    """
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager(excluded_plugins=excluded_plugins)
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

    _plugin_manager_instance.discover()
    return _plugin_manager_instance


def get_plugin_settings_provider(model_class: Type[T]):
    """
    This is a factory that creates a dependency provider function for a specific
    Pydantic settings model class. This allows type-hinted dependency injection
    of plugin-specific configurations in endpoints.

    Usage in an endpoint:
    `config: Annotated[MyPluginSettings, Depends(get_plugin_settings_provider(MyPluginSettings))]`
    """

    def dependency(request: Request) -> T:
        plugin_manager: PluginManager | None = getattr(
            request.app.state, "plugin_manager", None
        )
        if not plugin_manager:
            raise HTTPException(
                status_code=500,
                detail="Plugin manager not initialized in application state.",
            )

        config_instance = plugin_manager.get_plugin_config(model_class)

        if not config_instance:
            logger.error(
                "Configuration not found for model", model=model_class.__name__
            )
            raise HTTPException(
                status_code=500,
                detail=f"Configuration for '{model_class.__name__}' is not loaded. The server may be misconfigured.",
            )
        return config_instance

    return dependency
