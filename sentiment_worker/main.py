import asyncio
import json
from typing import List
import structlog
from bson import ObjectId
from config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
import redis.asyncio as redis
from kurisu_core.logging_config import setup_structlog
from kurisu_core.tracing import setup_tracing
from ml.coordinator import ModelCoordinator

setup_structlog(json_logs=settings.json_logs)
setup_tracing(service_name=settings.service_name)
logger = structlog.get_logger(__name__)


class SentimentWorker:
    """
    Worker that consumes message data from a Redis queue, performs sentiment
    and topic analysis, and updates the results in MongoDB.
    On startup, it launches a background task to find and enqueue any
    previously unanalyzed messages from the database using a sophisticated pipeline.
    """

    def __init__(self):
        self.redis_client = None
        self.mongo_client = None
        self.messages_collection = None
        self.model_coordinator = ModelCoordinator(
            sentiment_model_name=settings.sentiment_model,
            topics_model_name=settings.sensitive_topics_model,
            device_str=settings.model_device,
        )
        self.queue_name = "sentiment_analysis_queue"
        self.is_running = True
        self.SCAN_ENQUEUE_BATCH_SIZE = 1000

    async def connect(self):
        """Initializes connections to Redis and MongoDB."""
        self.redis_client = redis.from_url(
            str(settings.redis_url),
            password=settings.redis_password,
            decode_responses=True,
        )
        self.mongo_client = AsyncIOMotorClient(str(settings.mongodb_url))
        db = self.mongo_client[settings.mongodb_database]
        self.messages_collection = db.messages
        logger.info("Connections to Redis and MongoDB established.")

    async def disconnect(self):
        """Closes all active connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("Connections closed.")

    async def enqueue_missing_analyses(self):
        """
        Scans the database for messages that need analysis using an aggregation pipeline
        and enqueues their ID and content to the Redis queue for processing.
        """
        logger.info(
            "Starting background scan to enqueue unanalyzed messages using aggregation pipeline..."
        )
        cursor = None
        try:
            pipeline = [
                {
                    "$match": {
                        "$and": [
                            {"chat.type": {"$ne": "ChatType.PRIVATE"}},
                            {
                                "$or": [
                                    {"text": {"$exists": True, "$ne": ""}},
                                    {"caption": {"$exists": True, "$ne": ""}},
                                ]
                            },
                            {"$or": [{"event_type": "Message"}, {"_": "Message"}]},
                            {
                                "$or": [
                                    {"from_user.is_bot": {"$exists": False}},
                                    {"from_user.is_bot": False},
                                ]
                            },
                            {
                                "$or": [
                                    {"sentiment": {"$exists": False}},
                                    {"sentiment.positive": {"$exists": False}},
                                    {"sentiment.sensitive_topics": {"$exists": False}},
                                ]
                            },
                        ]
                    }
                },
                {"$addFields": {"message_content": {"$ifNull": ["$text", "$caption"]}}},
                {"$match": {"message_content": {"$not": {"$regex": "^/"}}}},
                {"$project": {"_id": 1, "message_content": 1}},
            ]

            cursor = self.messages_collection.aggregate(pipeline, allowDiskUse=True)
            item_batch = []
            total_enqueued = 0
            async for msg in cursor:
                item_to_enqueue = {
                    "_id": str(msg["_id"]),
                    "text": msg["message_content"],
                }
                item_batch.append(json.dumps(item_to_enqueue))

                if len(item_batch) >= self.SCAN_ENQUEUE_BATCH_SIZE:
                    await self.redis_client.lpush(self.queue_name, *item_batch)
                    total_enqueued += len(item_batch)
                    logger.info(
                        "Enqueued batch of historical messages",
                        batch_size=len(item_batch),
                        total_enqueued=total_enqueued,
                    )
                    item_batch = []
                    await asyncio.sleep(0.1)

            if item_batch:
                await self.redis_client.lpush(self.queue_name, *item_batch)
                total_enqueued += len(item_batch)

            logger.info(
                "Background scan completed.", total_messages_enqueued=total_enqueued
            )
        except Exception as e:
            logger.error(
                "Background scan for missing analyses failed.",
                error=str(e),
                exc_info=True,
            )
        finally:
            if cursor:
                await cursor.close()

    async def process_batch(self, batch_data: List[str]):
        """
        Processes a batch of message data from Redis: analyze content and update MongoDB.
        """
        log = logger.bind(batch_size=len(batch_data))
        log.info("Processing batch for analysis.")

        try:
            items = [json.loads(data) for data in batch_data]
        except json.JSONDecodeError:
            log.error(
                "Failed to parse JSON from batch data, skipping.", data=batch_data
            )
            return

        if not items:
            log.warning("Batch is empty after parsing.")
            return

        texts_to_analyze = [item.get("text", "") for item in items]
        analysis_results = self.model_coordinator.analyze_batch(texts_to_analyze)

        operations = []
        for item, analysis in zip(items, analysis_results):
            update_payload = {
                **analysis["sentiment"],
                "sensitive_topics": analysis["sensitive_topics"],
            }
            operations.append(
                UpdateOne(
                    {"_id": ObjectId(item["_id"])},
                    {"$set": {"sentiment": update_payload}},
                )
            )

        if operations:
            result = await self.messages_collection.bulk_write(
                operations, ordered=False
            )
            log.info("Batch updated in MongoDB.", modified_count=result.modified_count)

    async def run(self):
        """The main worker loop."""
        await self.connect()
        asyncio.create_task(self.enqueue_missing_analyses())
        log = logger.bind(queue=self.queue_name)
        log.info("Sentiment worker started, now consuming from Redis queue...")
        while self.is_running:
            try:
                batch_data = await self.redis_client.lpop(
                    self.queue_name, settings.batch_size
                )
                if not batch_data:
                    await asyncio.sleep(1)
                    continue
                if not isinstance(batch_data, list):
                    batch_data = [batch_data]

                await self.process_batch(batch_data)
            except Exception:
                log.exception("Error in worker loop, continuing...")
                await asyncio.sleep(5)

    async def shutdown(self):
        """Initiates a graceful shutdown of the worker."""
        self.is_running = False
        logger.info("Shutting down worker...")
        await self.disconnect()


async def main():
    """Entry point for the sentiment worker application."""
    worker = SentimentWorker()
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
