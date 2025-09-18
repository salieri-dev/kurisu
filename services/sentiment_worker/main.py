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
    previously unanalyzed messages from the database, using a Redis Set for deduplication.
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
        self.dedupe_set_name = "sentiment_jobs_in_queue"
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
        Scans for messages needing analysis in batches to avoid cursor timeouts and uses a Redis
        Set to prevent duplicate jobs from being added to the queue on restart.
        """
        logger.info("Starting background scan to enqueue unanalyzed messages...")
        total_enqueued = 0
        try:
            while self.is_running:
                pipeline = [
                    {
                        "$match": {
                            "$and": [
                                {"chat.type": {"$ne": "ChatType.PRIVATE"}},
                                {"_": "Message"},
                                {"sentiment": {"$exists": False}},
                                {
                                    "$or": [
                                        {"text": {"$exists": True, "$ne": ""}},
                                        {"caption": {"$exists": True, "$ne": ""}},
                                    ]
                                },
                                {
                                    "$or": [
                                        {"from_user.is_bot": {"$exists": False}},
                                        {"from_user.is_bot": False},
                                    ]
                                },
                            ]
                        }
                    },
                    {
                        "$addFields": {
                            "message_content": {"$ifNull": ["$text", "$caption"]}
                        }
                    },
                    {"$match": {"message_content": {"$not": {"$regex": "^/"}}}},
                    {"$project": {"_id": 1}},
                    {"$limit": self.SCAN_ENQUEUE_BATCH_SIZE},
                ]

                cursor = self.messages_collection.aggregate(pipeline)
                message_ids_to_process = [doc["_id"] async for doc in cursor]

                if not message_ids_to_process:
                    logger.info(
                        "No more messages to enqueue. Background scan finished."
                    )
                    break

                pipe = self.redis_client.pipeline()
                for msg_id in message_ids_to_process:
                    pipe.sismember(self.dedupe_set_name, str(msg_id))
                is_member_results = await pipe.execute()

                new_ids_to_enqueue = [
                    msg_id
                    for msg_id, is_member in zip(
                        message_ids_to_process, is_member_results
                    )
                    if not is_member
                ]

                if not new_ids_to_enqueue:
                    await asyncio.sleep(5)
                    continue

                await self.redis_client.sadd(
                    self.dedupe_set_name, *[str(mid) for mid in new_ids_to_enqueue]
                )

                content_cursor = self.messages_collection.find(
                    {"_id": {"$in": new_ids_to_enqueue}},
                    {"_id": 1, "text": 1, "caption": 1},
                )

                item_batch_json = []
                async for doc in content_cursor:
                    item_to_enqueue = {
                        "_id": str(doc["_id"]),
                        "text": doc.get("text") or doc.get("caption", ""),
                    }
                    item_batch_json.append(json.dumps(item_to_enqueue))

                if item_batch_json:
                    await self.redis_client.lpush(self.queue_name, *item_batch_json)
                    total_enqueued += len(item_batch_json)
                    logger.info(
                        "Enqueued batch of historical messages",
                        batch_size=len(item_batch_json),
                        total_enqueued=total_enqueued,
                    )

                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(
                "Background scan for missing analyses failed.",
                error=str(e),
                exc_info=True,
            )

        logger.info(
            "Background scan process has ended.", total_messages_enqueued=total_enqueued
        )

    async def process_batch(self, batch_data: List[str]):
        """
        Processes a batch of message data from Redis: analyze content, update MongoDB,
        and remove the processed IDs from the deduplication set.
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

        items.sort(key=lambda x: len(x.get("text", "")))
        texts_to_analyze = [item.get("text", "") for item in items]
        analysis_results = self.model_coordinator.analyze_batch(texts_to_analyze)

        operations = []
        processed_ids = []
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
            processed_ids.append(item["_id"])

        if operations:
            result = await self.messages_collection.bulk_write(
                operations, ordered=False
            )
            log.info("Batch updated in MongoDB.", modified_count=result.modified_count)

            if processed_ids:
                await self.redis_client.srem(self.dedupe_set_name, *processed_ids)
                log.info(
                    "Removed processed IDs from deduplication set.",
                    count=len(processed_ids),
                )

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
