# backend/plugins/core/config/service.py
import json
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
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, repository: ConfigRepository, redis_client: redis.Redis):
        self.repository = repository
        self.redis = redis_client

    async def get(self, key: str, default: Any = None) -> Any:
        # ... existing get method remains unchanged ...
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
            await self.redis.set(cache_key, value_to_cache, ex=self.CACHE_TTL_SECONDS)
        except Exception as e:
            logger.error("Redis error on SET", key=key, error=str(e))

        return config_item.value

    # --- NEW METHOD ---
    async def get_or_create(self, key: str, default: Any, description: str | None) -> Any:
        """
        Retrieves a config value. If it doesn't exist, it creates it
        with the provided default value and description, then returns the value.
        """
        # First, try a quick cache check.
        cache_key = f"{self.CACHE_PREFIX}{key}"
        try:
            cached_value = await self.redis.get(cache_key)
            if cached_value is not None:
                logger.debug("Config cache hit on get_or_create", key=key)
                return json.loads(cached_value)
        except Exception as e:
            logger.error("Redis error on GET in get_or_create", key=key, error=str(e))

        # Cache miss, check the database.
        logger.debug("Config cache miss on get_or_create", key=key)
        config_item = await self.repository.get_config(key)

        # If it exists in the database, cache it and return the value.
        if config_item:
            value_to_cache = json.dumps(config_item.value)
            try:
                await self.redis.set(cache_key, value_to_cache, ex=self.CACHE_TTL_SECONDS)
            except Exception as e:
                logger.error("Redis error on SET after DB find", key=key, error=str(e))
            return config_item.value

        # It doesn't exist in the database either. Create it.
        logger.info("Config key not found, creating with default value", key=key)
        new_config_item = await self.repository.upsert_config(
            key=key,
            value=default,
            description=description or f"Auto-initialized config for {key}"
        )

        # Cache the newly created default value.
        value_to_cache = json.dumps(new_config_item.value)
        try:
            await self.redis.set(cache_key, value_to_cache, ex=self.CACHE_TTL_SECONDS)
        except Exception as e:
            logger.error("Redis error on SET after create", key=key, error=str(e))
        
        return new_config_item.value
    # --- END NEW METHOD ---

    async def set(self, request: SetConfigRequest) -> ConfigGetResponse:
        # ... existing set method remains unchanged ...
        config_item = await self.repository.upsert_config(
            request.key, request.value, request.description
        )
        
        cache_key = f"{self.CACHE_PREFIX}{request.key}"
        try:
            await self.redis.delete(cache_key)
            logger.info("Config cache invalidated", key=request.key)
        except Exception as e:
            logger.error("Redis error on DELETE", key=request.key, error=str(e))

        return ConfigGetResponse.model_validate(config_item)
        
    async def get_full_config_item(self, key: str) -> ConfigGetResponse | None:
        # ... existing get_full_config_item method remains unchanged ...
        item = await self.repository.get_config(key)
        return ConfigGetResponse.model_validate(item) if item else None

# --- Dependency Injection Setup (No changes needed here) ---
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
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)]
) -> ConfigService:
    return ConfigService(repository, redis_client)