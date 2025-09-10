# sentiment_worker/main.py

import asyncio
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

# --- Setup ---
setup_structlog(json_logs=settings.json_logs)
setup_tracing(service_name=settings.service_name)
logger = structlog.get_logger(__name__)


# --- Worker Class ---
class SentimentWorker:
    """
    Worker that consumes message IDs from a Redis queue, performs sentiment
    and topic analysis, and updates the results in MongoDB.
    On startup, it launches a background task to find and enqueue any
    previously unanalyzed messages from the database.
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
        # Batch size for pushing IDs to Redis during the scan
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
        Scans the database for messages without sentiment analysis and adds their
        IDs to the Redis queue for processing. Runs as a background task.
        """
        logger.info("Starting background scan to enqueue unanalyzed messages...")
        cursor = None
        try:
            query = {
                "sentiment": {"$exists": False},
                "text": {"$exists": True, "$ne": None},
            }
            projection = {"_id": 1}
            cursor = self.messages_collection.find(
                query, projection, no_cursor_timeout=True
            )

            id_batch = []
            total_enqueued = 0
            async for msg in cursor:
                id_batch.append(str(msg["_id"]))
                if len(id_batch) >= self.SCAN_ENQUEUE_BATCH_SIZE:
                    await self.redis_client.lpush(self.queue_name, *id_batch)
                    total_enqueued += len(id_batch)
                    logger.info(
                        "Enqueued batch of historical messages",
                        batch_size=len(id_batch),
                        total_enqueued=total_enqueued,
                    )
                    id_batch = []
                    await asyncio.sleep(0.1)  # Yield control to the event loop

            if id_batch:
                await self.redis_client.lpush(self.queue_name, *id_batch)
                total_enqueued += len(id_batch)

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

    async def process_batch(self, message_ids: List[str]):
        """
        Processes a batch of message IDs: fetch, analyze, and update.
        """
        log = logger.bind(batch_size=len(message_ids))
        log.info("Processing batch for analysis.")

        try:
            object_ids = [ObjectId(id_str) for id_str in message_ids]
        except Exception:
            log.error("Invalid ObjectId found in batch, skipping.", ids=message_ids)
            return

        cursor = self.messages_collection.find(
            {"_id": {"$in": object_ids}, "text": {"$exists": True, "$ne": None}},
            {"text": 1},
        )
        messages = await cursor.to_list(length=len(object_ids))

        if not messages:
            log.warning("No messages with text found for the given IDs.")
            return

        texts_to_analyze = [msg.get("text", "") for msg in messages]
        analysis_results = self.model_coordinator.analyze_batch(texts_to_analyze)

        operations = []
        for msg, analysis in zip(messages, analysis_results):
            update_payload = {
                **analysis["sentiment"],
                "sensitive_topics": analysis["sensitive_topics"],
            }
            operations.append(
                UpdateOne({"_id": msg["_id"]}, {"$set": {"sentiment": update_payload}})
            )

        if operations:
            result = await self.messages_collection.bulk_write(
                operations, ordered=False
            )
            log.info("Batch updated in MongoDB.", modified_count=result.modified_count)

    async def run(self):
        """The main worker loop."""
        await self.connect()

        # Launch the full scan as a non-blocking background task
        asyncio.create_task(self.enqueue_missing_analyses())

        log = logger.bind(queue=self.queue_name)
        log.info("Sentiment worker started, now consuming from Redis queue...")

        while self.is_running:
            try:
                # Pop up to BATCH_SIZE items, with a timeout to allow graceful shutdown
                message_ids = await self.redis_client.lpop(
                    self.queue_name, settings.batch_size
                )
                if not message_ids:
                    await asyncio.sleep(1)  # Wait if queue is empty
                    continue

                if not isinstance(message_ids, list):
                    message_ids = [message_ids]

                await self.process_batch(message_ids)

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
