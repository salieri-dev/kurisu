from typing import Annotated, List
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from utils.dependencies import get_database, get_messages_collection
from .models import ChatProfileUpdate
from .repository import ChatsRepository


class ChatsService:
    def __init__(self, repository: ChatsRepository):
        self.repository = repository

    async def get_all_chat_ids(self) -> List[int]:
        return await self.repository.get_all_unique_chat_ids()

    async def bulk_upsert_profiles(self, updates: List[ChatProfileUpdate]) -> int:
        return await self.repository.upsert_chat_profiles(updates)


async def get_chats_collection(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    return db["chats"]


def get_chats_repository(
    messages_collection: Annotated[
        AsyncIOMotorCollection, Depends(get_messages_collection)
    ],
    chats_collection: Annotated[AsyncIOMotorCollection, Depends(get_chats_collection)],
) -> ChatsRepository:
    return ChatsRepository(messages_collection, chats_collection)


def get_chats_service(
    repository: Annotated[ChatsRepository, Depends(get_chats_repository)],
) -> ChatsService:
    return ChatsService(repository)
