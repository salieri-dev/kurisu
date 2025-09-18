from datetime import datetime
from typing import Annotated, Any, Dict
import redis.asyncio as redis
from fastapi import Depends
import structlog
from utils.dependencies import get_redis_client
from .models import SentimentQueueJob
from .repository import MessageRepository, get_message_repository

logger = structlog.get_logger(__name__)


class MessageService:
    """
    Service to handle message saving and enqueuing for sentiment analysis.
    This replaces the logic of the old 'worker' service.
    """

    SENTIMENT_QUEUE_NAME = "sentiment_analysis_queue"

    def __init__(
        self,
        repository: Annotated[MessageRepository, Depends(get_message_repository)],
        redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
    ):
        self.repository = repository
        self.redis = redis_client

    def _is_valid_for_analysis(self, message: Dict[str, Any]) -> bool:
        """
        Checks if a message from the queue is valid for sentiment analysis.
        """
        if message.get("chat", {}).get("type") == "ChatType.PRIVATE":
            return False
        if message.get("_") != "Message":
            return False
        if message.get("from_user", {}).get("is_bot", False):
            return False
        content = message.get("text") or message.get("caption")
        if not content:
            return False
        if content.startswith("/"):
            return False
        return True

    def _convert_dates(self, message_data: Dict[str, Any]):
        """
        Recursively find and convert date strings to datetime objects for DB storage.
        This ensures correct BSON Date types are used.
        """
        for key, value in message_data.items():
            if isinstance(value, dict):
                self._convert_dates(value)
            elif key in ("date", "created_at") and isinstance(value, str):
                try:
                    message_data[key] = datetime.fromisoformat(value)
                except ValueError:
                    logger.warning("Could not parse date string", key=key, value=value)
                    pass

    async def save_and_process_message(self, message_data: Dict[str, Any]) -> str:
        """
        Saves a message to MongoDB and, if it's valid, enqueues it for
        sentiment analysis.
        """

        self._convert_dates(message_data)

        inserted_id = await self.repository.save_one(message_data)

        structlog.contextvars.bind_contextvars(db_message_id=str(inserted_id))
        logger.info("Message saved to database")

        if self._is_valid_for_analysis(message_data):
            content = message_data.get("text") or message_data.get("caption", "")
            job = SentimentQueueJob(_id=str(inserted_id), text=content)

            await self.redis.lpush(self.SENTIMENT_QUEUE_NAME, job.model_dump_json())
            logger.info("Message enqueued for sentiment analysis")

        return str(inserted_id)


def get_message_service(
    service: Annotated[MessageService, Depends(MessageService)],
) -> MessageService:
    return service
