import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

logger = structlog.get_logger(__name__)

INDEX_DEFINITIONS = {
    "messages": [
        {"keys": [("from_user.id", ASCENDING)], "options": {}},
        {"keys": [("date", DESCENDING)], "options": {}},
        {"keys": [("chat.id", ASCENDING), ("date", DESCENDING)], "options": {}},
        {"keys": [("chat.type", ASCENDING)], "options": {}},
        {"keys": [("media", ASCENDING)], "options": {}},
    ],
    "chats": [
        {"keys": [("chat_id", ASCENDING)], "options": {"unique": True}},
    ],
    "chat_configs": [
        {
            "keys": [("chat_id", ASCENDING), ("param_name", ASCENDING)],
            "options": {"unique": True},
        },
    ],
    "configurations": [
        {"keys": [("key", ASCENDING)], "options": {"unique": True}},
    ],
    "threads": [
        {"keys": [("user_id", ASCENDING), ("created_at", DESCENDING)], "options": {}},
    ],
    "fanfics": [
        {"keys": [("user_id", ASCENDING), ("created_at", DESCENDING)], "options": {}},
    ],
    "ideograms": [
        {"keys": [("user_id", ASCENDING), ("created_at", DESCENDING)], "options": {}},
    ],
}


async def ensure_indexes(db: AsyncIOMotorDatabase):
    """
    Checks and creates all defined MongoDB indexes if they don't exist.

    This function is idempotent and safe to run on every application startup.
    It uses background index creation to avoid blocking the startup process.
    """
    logger.info("Starting database index verification and creation...")
    for collection_name, indexes in INDEX_DEFINITIONS.items():
        try:
            collection = db[collection_name]
            for index in indexes:
                keys = index["keys"]
                options = index.get("options", {})
                await collection.create_index(
                    keys,
                    background=True,
                    name=f"{collection_name}_{'_'.join([k[0] for k in keys])}_idx",
                    **options,
                )
            logger.info(
                f"Indexes ensured for collection '{collection_name}'",
                count=len(indexes),
            )
        except PyMongoError as e:
            logger.error(
                "Failed to create indexes for collection",
                collection=collection_name,
                error=str(e),
            )
    logger.info("Database index verification complete.")
