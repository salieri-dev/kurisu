from typing import Annotated
from fastapi import APIRouter, Depends
from .models import ChatIDListResponse, UpdateChatsRequest
from .service import ChatsService, get_chats_service

router = APIRouter()


@router.get("/all-ids", response_model=ChatIDListResponse)
async def get_all_chat_ids(
    service: Annotated[ChatsService, Depends(get_chats_service)],
):
    chat_ids = await service.get_all_chat_ids()
    return ChatIDListResponse(chat_ids=chat_ids)


@router.post("/profiles/update", summary="Upsert chat profiles")
async def update_chat_profiles(
    request: UpdateChatsRequest,
    service: Annotated[ChatsService, Depends(get_chats_service)],
):
    updated_count = await service.bulk_upsert_profiles(request.updates)
    return {"message": "Profiles updated successfully", "updated_count": updated_count}
