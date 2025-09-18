from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING
from .endpoint import router


class ChatConfigPlugin:
    name = "core/chat_config"
    version = "1.0.0"
    description = "Manages chat-specific configurations."

    async def setup(self, app: FastAPI, db: AsyncIOMotorDatabase):
        app.include_router(router, prefix=f"/{self.name}", tags=[self.name.title()])

        collection = db["chat_configs"]
        await collection.create_index(
            [("chat_id", ASCENDING), ("param_name", ASCENDING)],
            name="chat_config_compound_idx",
            unique=True,
            background=True,
        )
