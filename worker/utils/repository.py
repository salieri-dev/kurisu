from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError
from structlog import get_logger

logger = get_logger(__name__)


class ServiceError(Exception):
    """Custom exception for repository errors."""

    pass


class MessageRepository:
    """Handles database operations for messages."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def save_many(self, messages: list[dict[str, Any]]) -> int:
        """
        Saves a batch of messages to the database.
        Returns the number of successfully inserted messages.
        """
        if not messages:
            return 0
        try:
            result = await self._collection.insert_many(messages, ordered=False)
            return len(result.inserted_ids)
        except PyMongoError as e:
            logger.error("Database error during batch message insert", error=str(e))

            raise ServiceError(f"Batch insert database error: {e}") from e
