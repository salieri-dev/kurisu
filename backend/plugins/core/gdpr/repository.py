"""Repository layer for GDPR data operations."""

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError
from structlog import get_logger
from utils.exceptions import ServiceError

logger = get_logger(__name__)


class GDPRRepository:
    """Handles database operations for GDPR requests."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def delete_messages_by_user_id(self, user_id: int) -> int:
        """
        Deletes all messages for a given user ID.

        Args:
            user_id: The ID of the user whose messages to delete.

        Returns:
            The number of messages deleted.

        Raises:
            ServiceError: If a database error occurs.
        """
        try:
            delete_result = await self._collection.delete_many(
                {"from_user.id": user_id}
            )
            return delete_result.deleted_count
        except PyMongoError as e:
            logger.error(
                "Database error during GDPR message deletion",
                user_id=user_id,
                error=str(e),
            )
            raise ServiceError(f"Database error during GDPR deletion: {e}")
