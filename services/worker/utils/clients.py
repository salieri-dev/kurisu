import redis.asyncio as redis
from config import settings
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

WORKER_USER_AGENT = "KurisuWorker/1.0"


def create_redis_client() -> redis.Redis:
    """Factory to create a Redis client."""
    return redis.from_url(
        str(settings.redis_url), password=settings.redis_password, decode_responses=True
    )


def create_mongo_client() -> AsyncIOMotorClient:
    """Factory to create a MongoDB client."""
    return AsyncIOMotorClient(str(settings.mongodb_url))


redis_client = create_redis_client()
mongo_client = create_mongo_client()


def get_redis_client() -> redis.Redis:
    """Get the singleton Redis client instance."""
    return redis_client


def get_mongo_client() -> AsyncIOMotorClient:
    """Get the singleton MongoDB client instance."""
    return mongo_client


def get_mongo_database() -> AsyncIOMotorDatabase:
    """Get the default MongoDB database from the client."""
    return mongo_client[settings.mongodb_database]
