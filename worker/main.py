import asyncio
import json
import sys
import time
import uuid
from typing import Any, Optional

import structlog
from config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from redis.asyncio import Redis
from redis.exceptions import BusyLoadingError
from redis.exceptions import ConnectionError as RedisConnectionError
from utils.clients import get_mongo_client, get_mongo_database, get_redis_client
from utils.repository import MessageRepository, ServiceError

from kurisu_core.logging_config import setup_structlog


class MessageWorker:
    """Worker that processes messages from Redis and saves them directly to MongoDB."""

    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.redis_client: Optional[Redis] = None
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.repository: Optional[MessageRepository] = None
        self.logger = logger
        self.queue_name = "telegram_messages"
        self.retry_queue_name = "telegram_messages_retry"
        self.dead_letter_queue_name = "telegram_messages_dead_letter"
        self.processing_batch: list[dict[str, Any]] = []
        self.last_batch_sent_time = asyncio.get_event_loop().time()

    async def connect(self):
        """Initialize connections to Redis and MongoDB with a retry mechanism."""
        self.redis_client = get_redis_client()
        self.mongo_client = get_mongo_client()

        for attempt in range(settings.connect_retry_attempts):
            try:
                await self.redis_client.ping()
                self.logger.info("Successfully connected to Redis", attempt=attempt + 1)
                break
            except (BusyLoadingError, RedisConnectionError) as e:
                self.logger.warning(
                    "Could not connect to Redis, retrying...",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == settings.connect_retry_attempts - 1:
                    raise
                await asyncio.sleep(
                    settings.connect_retry_delay_seconds * (attempt + 1)
                )

        for attempt in range(settings.connect_retry_attempts):
            try:
                await self.mongo_client.admin.command("ping")
                self.logger.info(
                    "Successfully connected to MongoDB", attempt=attempt + 1
                )
                db = get_mongo_database()
                self.repository = MessageRepository(db.messages)
                break
            except ConnectionFailure as e:
                self.logger.warning(
                    "Could not connect to MongoDB, retrying...",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == settings.connect_retry_attempts - 1:
                    raise
                await asyncio.sleep(
                    settings.connect_retry_delay_seconds * (attempt + 1)
                )

    async def disconnect(self):
        """Close all connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.mongo_client:
            self.mongo_client.close()

    async def process_batch(self, messages: list[dict[str, Any]]) -> bool:
        """Save a batch of messages directly to MongoDB via the repository."""
        if not messages or not self.repository:
            return True

        correlation_id = messages[0].get("correlation_id") or str(uuid.uuid4())
        log = self.logger.bind(correlation_id=correlation_id, batch_size=len(messages))

        try:
            successful_saves = await self.repository.save_many(messages)
            log.info(
                "Batch processed successfully",
                successful=successful_saves,
                failed=len(messages) - successful_saves,
            )
            return True
        except ServiceError as e:
            log.error("Repository error during batch save", error=str(e))
            return False
        except Exception as e:
            log.error("Batch save failed unexpectedly", error=str(e), exc_info=True)
            return False

    async def process_message(self, message_data: str):
        """Process a single message from the queue."""
        try:
            message = json.loads(message_data)
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                message_id=message.get("id"),
                correlation_id=message.get("correlation_id", str(uuid.uuid4())),
            )
            log = structlog.get_logger()
            log.info("Processing message from queue")

            if "retry_count" not in message:
                message["retry_count"] = 0
            if "first_attempt_time" not in message:
                message["first_attempt_time"] = time.time()

            self.processing_batch.append(message)
            if len(self.processing_batch) >= settings.batch_size:
                await self.send_current_batch()

        except json.JSONDecodeError:
            self.logger.error("Failed to parse message JSON", message_data=message_data)
        except Exception:
            self.logger.exception("Error processing message")

    async def send_current_batch(self):
        """Send the current batch to the repository."""
        if not self.processing_batch:
            return

        batch_to_send = self.processing_batch.copy()
        self.processing_batch.clear()

        if await self.process_batch(batch_to_send):
            self.last_batch_sent_time = asyncio.get_event_loop().time()
        else:
            await self.handle_failed_batch(batch_to_send)

    async def handle_failed_batch(self, batch: list[dict[str, Any]]):
        """Handle failed batch with retries and dead letter queue."""
        for message in batch:
            log = self.logger.bind(message_id=message.get("id"))
            try:
                retry_count = message.get("retry_count", 0) + 1
                if retry_count > settings.max_retry_attempts:
                    await self.redis_client.lpush(
                        self.dead_letter_queue_name, json.dumps(message)
                    )
                    log.error(
                        "Message moved to dead letter queue", retry_count=retry_count
                    )
                else:
                    message["retry_count"] = retry_count
                    await self.redis_client.lpush(
                        self.retry_queue_name, json.dumps(message)
                    )
                    log.warning("Message scheduled for retry", retry_count=retry_count)
            except Exception as e:
                log.error(
                    "Failed to handle failed message", error=str(e), exc_info=True
                )

    async def run(self):
        """Main worker loop."""
        try:
            await self.connect()
        except Exception:
            self.logger.fatal(
                "Could not establish initial connections to services. Shutting down."
            )
            raise

        self.logger.info("Message worker started successfully.")
        try:
            while True:
                try:
                    message_data = await self.redis_client.brpop(
                        [self.queue_name], timeout=1
                    )
                    if message_data:
                        _, message_json = message_data
                        await self.process_message(message_json)

                    time_since_last_batch = (
                        asyncio.get_event_loop().time() - self.last_batch_sent_time
                    )
                    if (
                        self.processing_batch
                        and time_since_last_batch >= settings.batch_timeout_seconds
                    ):
                        self.logger.info("Sending batch due to timeout")
                        await self.send_current_batch()
                except asyncio.CancelledError:
                    break
                except (RedisConnectionError, ConnectionFailure):
                    self.logger.exception(
                        "Connection lost to a dependency, attempting to reconnect..."
                    )
                    await asyncio.sleep(5)
                    await self.connect()
                except Exception:
                    self.logger.exception(
                        "Unhandled error in worker loop, continuing..."
                    )
                    await asyncio.sleep(1)
        finally:
            if self.processing_batch:
                self.logger.info("Sending final batch before shutdown")
                await self.send_current_batch()
            await self.disconnect()
            self.logger.info("Worker has shut down")


async def main():
    """Main entry point."""
    setup_structlog(json_logs=settings.json_logs)
    logger = structlog.get_logger(__name__)
    worker = MessageWorker(logger=logger)

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.fatal("Worker failed critically", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
