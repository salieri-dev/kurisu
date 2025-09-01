# backend/utils/dependencies.py
"""FastAPI dependencies for request validation and database connections."""

from typing import Annotated

import redis.asyncio as redis
from config import settings
from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from utils.fal_client import FalAIClient

from .llm_client import LLMClient
from .redis_client import get_redis_client as redis_client_factory


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


async def get_redis_client() -> redis.Redis:
    """
    Dependency to get the shared Redis client instance.
    """
    return redis_client_factory()


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


_llm_client_instance = None


def get_llm_client() -> LLMClient:
    """
    Dependency provider for the LLMClient.
    Uses a singleton pattern to reuse the client instance.
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient(
            api_key=settings.llm_api_key,
            base_url=str(settings.llm_base_url),
            http_referer=settings.llm_http_referer,
            x_title=settings.llm_x_title,
        )
    return _llm_client_instance


_fal_client_instance = None


def get_fal_client() -> FalAIClient:
    """Dependency provider for the FalAIClient."""
    global _fal_client_instance
    if _fal_client_instance is None:
        _fal_client_instance = FalAIClient(api_key=settings.fal_api_key)
    return _fal_client_instance
