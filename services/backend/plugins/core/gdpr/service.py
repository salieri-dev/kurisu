"""Service layer for GDPR operations."""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from plugins.core.gdpr.models import GDPRDeleteRequest, GDPRDeleteResponse
from plugins.core.gdpr.repository import GDPRRepository
from structlog import get_logger
from utils.dependencies import get_messages_collection
from utils.exceptions import ServiceError

logger = get_logger(__name__)


class GDPRService:
    """Service for handling GDPR data deletion operations."""

    def __init__(self, repository: GDPRRepository):
        self.repository = repository

    async def delete_user_data(self, request: GDPRDeleteRequest) -> GDPRDeleteResponse:
        """
        Delete all messages for a specific user (GDPR compliance).
        """
        try:
            user_id = request.user_id

            deleted_count = await self.repository.delete_messages_by_user_id(user_id)

            logger.info(
                "GDPR deletion completed for user",
                user_id=user_id,
                deleted_count=deleted_count,
            )
            return GDPRDeleteResponse(success=True, deleted_count=deleted_count)

        except ServiceError:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during GDPR deletion",
                user_id=request.user_id,
                error=str(e),
                exc_info=True,
            )
            raise ServiceError(f"An unexpected error occurred: {e}") from e


async def get_gdpr_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_messages_collection)],
) -> GDPRRepository:
    return GDPRRepository(collection)


async def get_gdpr_service(
    repository: Annotated[GDPRRepository, Depends(get_gdpr_repository)],
) -> GDPRService:
    return GDPRService(repository)
