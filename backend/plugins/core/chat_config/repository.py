"""Repository layer for chat configuration data operations."""

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError
from structlog import get_logger
from utils.exceptions import ServiceError

logger = get_logger(__name__)


class ChatConfigRepository:
    """Handles all database operations for chat configurations."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def find_one_config(
        self, chat_id: int, param_name: str
    ) -> Optional[dict[str, Any]]:
        """Finds a single configuration parameter for a chat."""
        try:
            return await self._collection.find_one(
                {"chat_id": chat_id, "param_name": param_name}
            )
        except PyMongoError as e:
            logger.error(
                "DB error finding one chat config",
                chat_id=chat_id,
                param_name=param_name,
                error=str(e),
            )
            raise ServiceError(f"Database error while finding config: {e}")

    async def find_all_configs_for_chat(self, chat_id: int) -> list[dict[str, Any]]:
        """Finds all configuration parameters for a given chat."""
        try:
            cursor = self._collection.find({"chat_id": chat_id})
            return await cursor.to_list(length=None)
        except PyMongoError as e:
            logger.error(
                "DB error finding all chat configs", chat_id=chat_id, error=str(e)
            )
            raise ServiceError(f"Database error while finding all configs: {e}")

    async def upsert_config(
        self, query: dict[str, Any], update: dict[str, Any]
    ) -> None:
        """Creates or updates a configuration parameter."""
        try:
            await self._collection.update_one(query, update, upsert=True)
        except PyMongoError as e:
            logger.error("DB error upserting chat config", query=query, error=str(e))
            raise ServiceError(f"Database error while setting config: {e}")
