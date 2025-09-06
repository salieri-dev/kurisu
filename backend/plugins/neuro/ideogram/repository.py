from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError
from structlog import get_logger
from utils.dependencies import get_database
from utils.exceptions import ServiceError

from .models import IdeogramDB

logger = get_logger(__name__)


class IdeogramRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def save_generation(self, data: IdeogramDB) -> str:
        try:
            result = await self._collection.insert_one(data.model_dump())
            logger.info("Saved Ideogram generation to database", user_id=data.user_id)
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error("Database error saving Ideogram generation", error=str(e))
            raise ServiceError(
                "Failed to save generation due to a database error."
            ) from e


async def get_ideogram_collection(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    return db["ideograms"]


async def get_ideogram_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_ideogram_collection)],
) -> IdeogramRepository:
    return IdeogramRepository(collection)
