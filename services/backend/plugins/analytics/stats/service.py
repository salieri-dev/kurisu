import asyncio
from typing import Annotated
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection

from utils.dependencies import get_messages_collection
from .models import FullStatsResponse, CountByGroup, TopChatItem, TopUserItem
from .repository import StatsRepository


class StatsService:
    def __init__(self, repository: StatsRepository):
        self.repository = repository

    async def get_full_stats(self) -> FullStatsResponse:
        tasks = {
            "total_messages": self.repository.get_total_count(),
            "total_users": self.repository.get_unique_user_count(),
            "mau": self.repository.get_unique_user_count(days=30),
            "cmd_mau": self.repository.get_monthly_command_user_count(),
            "chats_by_type": self.repository.get_count_by_group("chat.type"),
            "media_by_type": self.repository.get_count_by_group("media"),
            "top_chats": self.repository.get_top_chats(),
            "top_users": self.repository.get_top_monthly_active_users(),
            "hourly": self.repository.get_hourly_activity(),
        }
        results = await asyncio.gather(*tasks.values())
        data = dict(zip(tasks.keys(), results))

        most_active, least_active = None, None
        if data["hourly"]:
            sorted_by_count = sorted(data["hourly"], key=lambda x: x["count"])
            if sorted_by_count:
                most_active = sorted_by_count[-1]["group"]
                least_active = sorted_by_count[0]["group"]

        return FullStatsResponse(
            total_messages=data["total_messages"],
            total_unique_users=data["total_users"],
            monthly_active_users=data["mau"],
            monthly_command_users=data["cmd_mau"],
            most_active_hour_moscow=most_active,
            least_active_hour_moscow=least_active,
            messages_by_chat_type=[
                CountByGroup(**item) for item in data["chats_by_type"]
            ],
            messages_by_media_type=[
                CountByGroup(group=item["group"] or "text", count=item["count"])
                for item in data["media_by_type"]
            ],
            top_10_chats=[TopChatItem(**item) for item in data["top_chats"]],
            top_10_monthly_active_users=[
                TopUserItem(**item) for item in data["top_users"]
            ],
        )


def get_stats_repository(
    collection: Annotated[AsyncIOMotorCollection, Depends(get_messages_collection)],
) -> StatsRepository:
    return StatsRepository(collection)


def get_stats_service(
    repository: Annotated[StatsRepository, Depends(get_stats_repository)],
) -> StatsService:
    return StatsService(repository)
