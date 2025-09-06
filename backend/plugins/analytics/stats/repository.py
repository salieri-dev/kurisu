from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection
from structlog import get_logger

logger = get_logger(__name__)


class StatsRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.command_regex = r"^/(\w+)(\s|$)"

    async def get_total_count(self) -> int:
        return await self.collection.count_documents({})

    async def get_count_by_group(self, group_field: str) -> list[dict]:
        pipeline = [
            {"$group": {"_id": f"${group_field}", "count": {"$sum": 1}}},
            {"$project": {"group": "$_id", "count": 1, "_id": 0}},
            {"$sort": {"count": -1}},
        ]
        return await self.collection.aggregate(pipeline).to_list(length=None)

    async def get_unique_user_count(self, days: int | None = None) -> int:
        match_stage = {}
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            match_stage = {"date": {"$gte": start_date}}

        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$from_user.id"}},
            {"$count": "unique_users"},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        return result[0]["unique_users"] if result else 0

    async def get_monthly_command_user_count(self) -> int:
        start_date = datetime.utcnow() - timedelta(days=30)
        pipeline = [
            {
                "$match": {
                    "date": {"$gte": start_date},
                    "text": {"$regex": self.command_regex},
                }
            },
            {"$group": {"_id": "$from_user.id"}},
            {"$count": "command_users"},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        return result[0]["command_users"] if result else 0

    async def get_top_chats(self, limit: int = 10) -> list[dict]:
        pipeline = [
            {
                "$match": {
                    "chat.type": {"$in": ["ChatType.GROUP", "ChatType.SUPERGROUP"]}
                }
            },
            {
                "$group": {
                    "_id": "$chat.id",
                    "title": {"$first": "$chat.title"},
                    "type": {"$first": "$chat.type"},
                    "message_count": {"$sum": 1},
                }
            },
            {"$sort": {"message_count": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "chat_id": "$_id",
                    "title": 1,
                    "type": 1,
                    "message_count": 1,
                    "_id": 0,
                }
            },
        ]
        return await self.collection.aggregate(pipeline).to_list(length=limit)

    async def get_top_monthly_active_users(self, limit: int = 10) -> list[dict]:
        start_date = datetime.utcnow() - timedelta(days=30)
        pipeline = [
            {"$match": {"date": {"$gte": start_date}, "from_user.id": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$from_user.id",
                    "username": {"$first": "$from_user.username"},
                    "first_name": {"$first": "$from_user.first_name"},
                    "message_count": {"$sum": 1},
                }
            },
            {"$sort": {"message_count": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "user_id": "$_id",
                    "display_name": {"$ifNull": ["$username", "$first_name"]},
                    "message_count": 1,
                    "_id": 0,
                }
            },
        ]
        return await self.collection.aggregate(pipeline).to_list(length=limit)

    async def get_hourly_activity(self) -> list[dict]:
        start_date = datetime.utcnow() - timedelta(days=30)
        pipeline = [
            {"$match": {"date": {"$gte": start_date}}},
            {
                "$addFields": {
                    "moscow_hour": {"$hour": {"$add": ["$date", 3 * 60 * 60 * 1000]}}
                }
            },
            {"$group": {"_id": "$moscow_hour", "count": {"$sum": 1}}},
            {"$project": {"group": "$_id", "count": 1, "_id": 0}},
            {"$sort": {"_id": 1}},
        ]
        return await self.collection.aggregate(pipeline).to_list(length=24)
