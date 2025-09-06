from datetime import datetime
from typing import List
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import UpdateOne
from structlog import get_logger
from .models import ChatProfileUpdate, StatusHistoryEntry

logger = get_logger(__name__)


class ChatsRepository:
    def __init__(
        self,
        messages_collection: AsyncIOMotorCollection,
        chats_collection: AsyncIOMotorCollection,
    ):
        self.messages = messages_collection
        self.chats = chats_collection

    async def get_all_unique_chat_ids(self) -> List[int]:
        pipeline = [
            {
                "$match": {
                    "chat.type": {"$in": ["ChatType.GROUP", "ChatType.SUPERGROUP"]}
                }
            },
            {"$group": {"_id": "$chat.id"}},
        ]
        chat_docs = await self.messages.aggregate(pipeline).to_list(length=None)
        return [doc["_id"] for doc in chat_docs if doc and doc.get("_id")]

    async def upsert_chat_profiles(self, updates: List[ChatProfileUpdate]) -> int:
        if not updates:
            return 0

        bulk_operations = []
        now = datetime.utcnow()

        for update in updates:
            new_history_entry = StatusHistoryEntry(
                status=update.status, timestamp=now
            ).model_dump()

            pipeline = [
                {
                    "$set": {
                        "chat_info": update.chat_info,
                        "current_status": update.status,
                        "last_updated": now,
                        "first_seen": {"$ifNull": ["$first_seen", now]},
                        "status_history": {
                            "$cond": {
                                "if": {"$ne": ["$current_status", update.status]},
                                "then": {
                                    "$slice": [
                                        {
                                            "$concatArrays": [
                                                {"$ifNull": ["$status_history", []]},
                                                [new_history_entry],
                                            ]
                                        },
                                        -50,
                                    ]
                                },
                                "else": "$status_history",
                            }
                        },
                    }
                }
            ]

            op = UpdateOne({"chat_id": update.chat_id}, pipeline, upsert=True)
            bulk_operations.append(op)

        result = await self.chats.bulk_write(bulk_operations, ordered=False)
        return result.upserted_count + result.modified_count
