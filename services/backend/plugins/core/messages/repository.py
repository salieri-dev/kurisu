from typing import Annotated, Any, Dict
from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError
import structlog
from utils.dependencies import get_messages_collection
from utils.exceptions import ServiceError

logger = structlog.get_logger(__name__)


class MessageRepository:
    """Handles database operations for storing messages."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def save_one(self, message_data: Dict[str, Any]) -> ObjectId:
        """Saves a single message to the database."""
        try:
            result = await self._collection.insert_one(message_data)
            return result.inserted_id
        except PyMongoError as e:
            logger.error("Database error during message insert", error=str(e))
            raise ServiceError(f"Message insert database error: {e}") from e


def get_message_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_messages_collection)],
) -> MessageRepository:
    return MessageRepository(collection)
