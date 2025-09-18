from datetime import datetime, time
from typing import Annotated, Any, Dict, List

from fastapi import Depends
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.errors import PyMongoError
from structlog import get_logger

from utils.dependencies import get_database, get_messages_collection
from utils.exceptions import ServiceError
from .models import SummaryDB

log = get_logger(__name__)


class MessageRepository:
    """Repository for fetching messages required for summarization."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def get_messages_for_summary(
        self, chat_id: int, target_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetches all relevant messages for a specific chat on a given date (UTC).
        Excludes commands and messages from bots.
        """
        start_of_day = datetime.combine(
            target_date.date(), time.min, tzinfo=datetime.now().astimezone().tzinfo
        )
        end_of_day = datetime.combine(
            target_date.date(), time.max, tzinfo=datetime.now().astimezone().tzinfo
        )

        start_utc = start_of_day.astimezone(datetime.now().astimezone().tzinfo.utc)
        end_utc = end_of_day.astimezone(datetime.now().astimezone().tzinfo.utc)

        query = {
            "chat.id": chat_id,
            "date": {"$gte": start_utc, "$lte": end_utc},
            "$or": [
                {"from_user.is_bot": {"$exists": False}},
                {"from_user.is_bot": False},
            ],
            "text": {"$not": {"$regex": "^/"}},
        }
        try:
            cursor = self._collection.find(query).sort("date", 1)
            return await cursor.to_list(length=None)
        except PyMongoError as e:
            log.error(
                "DB error fetching messages for summary", error=str(e), chat_id=chat_id
            )
            raise ServiceError("Database error while fetching messages.") from e


class SummaryRepository:
    """Repository for storing and retrieving generated chat summaries."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def store_summary(self, summary_data: SummaryDB) -> str:
        """Stores a generated summary in the database."""
        try:
            result = await self._collection.insert_one(summary_data.model_dump())
            log.info(
                "Stored summary in database",
                chat_id=summary_data.chat_id,
                summary_id=str(result.inserted_id),
            )
            return str(result.inserted_id)
        except PyMongoError as e:
            log.error(
                "DB error storing summary", error=str(e), chat_id=summary_data.chat_id
            )
            raise ServiceError("Database error while storing summary.") from e


async def get_summaries_collection(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    """Dependency provider for the 'summaries' collection."""
    return db["summaries"]


def get_summary_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_summaries_collection)],
) -> SummaryRepository:
    """Dependency provider for the SummaryRepository."""
    return SummaryRepository(collection)


def get_message_repository_for_summary(
    messages_collection: Annotated[
        AsyncIOMotorCollection, Depends(get_messages_collection)
    ],
) -> MessageRepository:
    """Dependency provider for the MessageRepository, using the main 'messages' collection."""
    return MessageRepository(messages_collection)
