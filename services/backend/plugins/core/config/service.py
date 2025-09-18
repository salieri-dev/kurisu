import json
import time
from typing import Annotated, Any
import redis.asyncio as redis
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from structlog import get_logger
from utils.dependencies import get_database, get_redis_client
from .models import ConfigGetResponse, SetConfigRequest
from .repository import ConfigRepository

logger = get_logger(__name__)


class ConfigService:
    """
    Service layer for managing configurations with a caching layer.
    Orchestrates reads/writes between Redis cache and MongoDB persistence.
    """

    CACHE_PREFIX = "config:"
    DEFAULT_CACHE_TTL_SECONDS = 60
    TTL_CONFIG_KEY = "core/config.ttl_seconds"

    def __init__(self, repository: ConfigRepository, redis_client: redis.Redis):
        self.repository = repository
        self.redis = redis_client
        self._current_ttl: int | None = None
        self._ttl_last_refreshed: float = 0
        self._ttl_refresh_interval: int = 10

    async def _get_current_ttl(self) -> int:
        """
        Gets the current cache TTL.
        It caches the TTL value itself for a short period to avoid checking Redis/DB
        on every single request, making it highly efficient.
        """
        now = time.time()
        if (
            self._current_ttl is not None
            and (now - self._ttl_last_refreshed) < self._ttl_refresh_interval
        ):
            return self._current_ttl
        ttl_value = await self.get(
            self.TTL_CONFIG_KEY, default=self.DEFAULT_CACHE_TTL_SECONDS
        )
        if not isinstance(ttl_value, int) or ttl_value <= 0:
            ttl_value = self.DEFAULT_CACHE_TTL_SECONDS
        self._current_ttl = ttl_value
        self._ttl_last_refreshed = now
        return self._current_ttl

    async def get(self, key: str, default: Any = None) -> Any:
        cache_key = f"{self.CACHE_PREFIX}{key}"
        try:
            cached_value = await self.redis.get(cache_key)
            if cached_value is not None:
                logger.debug("Config cache hit", key=key)
                return json.loads(cached_value)
        except Exception as e:
            logger.error("Redis error on GET", key=key, error=str(e))
        logger.debug("Config cache miss", key=key)
        config_item = await self.repository.get_config(key)
        if not config_item:
            return default
        value_to_cache = json.dumps(config_item.value)
        try:
            ttl = await self._get_current_ttl()
            await self.redis.set(cache_key, value_to_cache, ex=ttl)
        except Exception as e:
            logger.error("Redis error on SET", key=key, error=str(e))
        return config_item.value

    async def get_or_create(
        self, key: str, default: Any, description: str | None
    ) -> Any:
        """
        Retrieves a config value. If it doesn't exist, it creates it
        with the provided default value and description, then returns the value.
        """
        cache_key = f"{self.CACHE_PREFIX}{key}"
        try:
            cached_value = await self.redis.get(cache_key)
            if cached_value is not None:
                logger.debug("Config cache hit on get_or_create", key=key)
                return json.loads(cached_value)
        except Exception as e:
            logger.error("Redis error on GET in get_or_create", key=key, error=str(e))
        logger.debug("Config cache miss on get_or_create", key=key)
        config_item = await self.repository.get_config(key)
        if config_item:
            value_to_cache = json.dumps(config_item.value)
            try:
                ttl = await self._get_current_ttl()
                await self.redis.set(cache_key, value_to_cache, ex=ttl)
            except Exception as e:
                logger.error("Redis error on SET after DB find", key=key, error=str(e))
            return config_item.value
        logger.info("Config key not found, creating with default value", key=key)
        new_config_item = await self.repository.upsert_config(
            key=key,
            value=default,
            description=description or f"Auto-initialized config for {key}",
        )
        value_to_cache = json.dumps(new_config_item.value)
        try:
            ttl = await self._get_current_ttl()
            await self.redis.set(cache_key, value_to_cache, ex=ttl)
        except Exception as e:
            logger.error("Redis error on SET after create", key=key, error=str(e))
        return new_config_item.value

    async def set(self, request: SetConfigRequest) -> ConfigGetResponse:
        config_item = await self.repository.upsert_config(
            request.key, request.value, request.description
        )
        cache_key = f"{self.CACHE_PREFIX}{request.key}"
        try:
            await self.redis.delete(cache_key)
            logger.info("Config cache invalidated", key=request.key)
            if request.key == self.TTL_CONFIG_KEY:
                self._ttl_last_refreshed = 0
                logger.info("TTL config key was updated, forcing refresh on next call.")
        except Exception as e:
            logger.error("Redis error on DELETE", key=request.key, error=str(e))
        return ConfigGetResponse.model_validate(config_item)

    async def get_full_config_item(self, key: str) -> ConfigGetResponse | None:
        item = await self.repository.get_config(key)
        return ConfigGetResponse.model_validate(item) if item else None

    async def get_all_configs(self) -> list[ConfigGetResponse]:
        """
        Retrieves all configuration items directly from the database, bypassing cache.
        This is intended for admin/dashboard use.
        """
        items = await self.repository.get_all_configs()
        return [ConfigGetResponse.model_validate(item.model_dump()) for item in items]

    async def clear_cache_for_key(self, key: str) -> bool:
        """Invalidates the Redis cache for a specific configuration key."""
        cache_key = f"{self.CACHE_PREFIX}{key}"
        try:
            deleted_count = await self.redis.delete(cache_key)
            if deleted_count > 0:
                logger.info("Config cache explicitly invalidated", key=key)
            if key == self.TTL_CONFIG_KEY:
                self._ttl_last_refreshed = 0
                logger.info(
                    "TTL config key cache was cleared, forcing refresh on next call."
                )
            return deleted_count > 0
        except Exception as e:
            logger.error("Redis error on explicit DELETE", key=key, error=str(e))
            return False


async def get_config_collection(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    return database["configurations"]


async def get_config_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_config_collection)],
) -> ConfigRepository:
    return ConfigRepository(collection)


async def get_config_service(
    repository: Annotated[ConfigRepository, Depends(get_config_repository)],
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
) -> ConfigService:
    return ConfigService(repository, redis_client)
