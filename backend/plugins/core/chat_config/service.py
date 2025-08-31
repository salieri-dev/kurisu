"""Service layer for chat configuration operations."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from plugins.core.chat_config.models import ChatConfig
from plugins.core.chat_config.repository import ChatConfigRepository
from structlog import get_logger
from utils.dependencies import get_database
from utils.exceptions import ServiceError

logger = get_logger(__name__)


class ChatConfigService:
    """Service for handling chat configuration operations."""

    def __init__(self, repository: ChatConfigRepository):
        self.repository = repository

    async def set_config(
        self, chat_id: int, param_name: str, param_value: Any
    ) -> ChatConfig:
        """Set or update a configuration parameter for a specific chat."""
        try:
            query = {"chat_id": chat_id, "param_name": param_name}
            update = {
                "$set": {
                    "param_value": param_value,
                    "updated_at": datetime.now(UTC),
                }
            }

            await self.repository.upsert_config(query, update)

            logger.info(
                "Set chat config",
                chat_id=chat_id,
                param_name=param_name,
                param_value=param_value,
            )
            return ChatConfig(
                chat_id=chat_id, param_name=param_name, param_value=param_value
            )
        except ServiceError:
            raise
        except Exception as e:
            logger.error("Unexpected error in set_config service", error=str(e))
            raise ServiceError(f"Unexpected error: {e}")

    async def get_config(self, chat_id: int, param_name: str) -> ChatConfig | None:
        """Get a configuration parameter for a specific chat."""
        try:
            document = await self.repository.find_one_config(chat_id, param_name)
            if document:
                logger.info("Retrieved chat config", **document)

                return ChatConfig(**document)
            logger.info("Chat config not found", chat_id=chat_id, param_name=param_name)
            return None
        except ServiceError:
            raise
        except Exception as e:
            logger.error("Unexpected error in get_config service", error=str(e))
            raise ServiceError(f"Unexpected error: {e}")

    async def get_all_configs_for_chat(self, chat_id: int) -> dict[str, Any]:
        """Get all configuration parameters for a specific chat."""
        try:
            documents = await self.repository.find_all_configs_for_chat(chat_id)
            configs: dict[str, Any] = {
                doc.get("param_name"): doc.get("param_value")
                for doc in documents
                if doc.get("param_name")
            }
            logger.info(
                "Retrieved all chat configs", chat_id=chat_id, count=len(configs)
            )
            return configs
        except ServiceError:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in get_all_configs_for_chat service", error=str(e)
            )
            raise ServiceError(f"Unexpected error: {e}")


async def get_chat_configs_collection(
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> AsyncIOMotorCollection:
    return database["chat_configs"]


async def get_chat_config_repository(
    collection: AsyncIOMotorCollection = Depends(get_chat_configs_collection),
) -> ChatConfigRepository:
    return ChatConfigRepository(collection)


async def get_chat_config_service(
    repository: ChatConfigRepository = Depends(get_chat_config_repository),
) -> ChatConfigService:
    return ChatConfigService(repository)
