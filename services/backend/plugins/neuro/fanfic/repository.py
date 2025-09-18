from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError
from structlog import get_logger
from utils.dependencies import get_database
from utils.exceptions import ServiceError

from .models import FanficDB

logger = get_logger(__name__)


class FanficRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def save_fanfic(self, fanfic_data: FanficDB) -> str:
        try:
            result = await self._collection.insert_one(fanfic_data.model_dump())
            logger.info("Saved fanfic to database", user_id=fanfic_data.user_id)
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error("Database error saving fanfic", error=str(e))
            raise ServiceError("Failed to save fanfic due to a database error.") from e


async def get_fanfics_collection(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    return db["fanfics"]


async def get_fanfic_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_fanfics_collection)],
) -> FanficRepository:
    return FanficRepository(collection)
