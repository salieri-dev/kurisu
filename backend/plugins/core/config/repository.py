from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError
from structlog import get_logger
from utils.exceptions import ServiceError

from .models import ConfigItem

logger = get_logger(__name__)


class ConfigRepository:
    """Handles all database operations for the 'configurations' collection."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def get_config(self, key: str) -> ConfigItem | None:
        """Retrieves a single configuration item from the database by its key."""
        try:
            doc = await self._collection.find_one({"key": key})
            return ConfigItem(**doc) if doc else None
        except PyMongoError as e:
            logger.error("DB error getting config", key=key, error=str(e))
            raise ServiceError(f"Database error while getting config for key '{key}'")

    async def upsert_config(
        self, key: str, value: Any, description: str | None
    ) -> ConfigItem:
        """Creates a new configuration item or updates an existing one."""
        try:
            now = datetime.utcnow()
            update_doc = {
                "$set": {
                    "value": value,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "key": key,
                    "created_at": now,
                },
            }
            if description is not None:
                update_doc["$set"]["description"] = description

            result = await self._collection.find_one_and_update(
                {"key": key}, update_doc, upsert=True, return_document=True
            )
            return ConfigItem(**result)
        except PyMongoError as e:
            logger.error("DB error upserting config", key=key, error=str(e))
            raise ServiceError(f"Database error while setting config for key '{key}'")
