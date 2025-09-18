from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError
from structlog import get_logger
from utils.dependencies import get_database
from utils.exceptions import ServiceError

from .models import ThreadDB

logger = get_logger(__name__)


class ThreadsRepository:
    """Repository for managing thread data in MongoDB."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def save_thread(self, thread_data: ThreadDB) -> str:
        """Saves a generated thread to the database."""
        try:
            result = await self._collection.insert_one(thread_data.model_dump())
            logger.info(
                "Saved thread to database",
                user_id=thread_data.user_id,
                command=thread_data.command,
            )
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error("Database error saving thread", error=str(e))
            raise ServiceError("Failed to save thread due to a database error.") from e


async def get_threads_collection(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    return database["threads"]


async def get_threads_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_threads_collection)],
) -> ThreadsRepository:
    return ThreadsRepository(collection)
