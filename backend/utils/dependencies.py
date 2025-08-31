"""FastAPI dependencies for request validation and database connections."""

from typing import Annotated

from config import settings
from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)


async def require_telegram_headers(request: Request) -> dict:
    """
    Dependency to require Telegram-specific headers.
    """
    x_user_id = request.headers.get("x-user-id")
    x_chat_id = request.headers.get("x-chat-id")

    if not x_user_id or not x_chat_id:
        raise HTTPException(
            status_code=400, detail="Both x-user-id and x-chat-id headers are required"
        )

    return {"user_id": x_user_id, "chat_id": x_chat_id}


async def get_mongo_client(request: Request) -> AsyncIOMotorClient:
    """
    Dependency to get the MongoDB client instance from the application state.
    """
    return request.app.state.mongo_client


async def get_database(
    client: Annotated[AsyncIOMotorClient, Depends(get_mongo_client)],
) -> AsyncIOMotorDatabase:
    """
    Dependency to get the application's default MongoDB database.
    """
    return client[settings.mongodb_database]


async def get_messages_collection(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    """
    Dependency to get the 'messages' collection.
    """
    return database.messages


async def get_collection(
    collection_name: str,
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AsyncIOMotorCollection:
    """
    Generic dependency to get any MongoDB collection by name.
    NOTE: This cannot be used directly as a dependency in routes due to the
    `collection_name` argument. It's a helper for other dependency providers.
    """
    return database[collection_name]
