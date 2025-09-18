from typing import Annotated

from fastapi import APIRouter, Depends
from utils.dependencies import require_telegram_headers
from .models import AlbumResponse
from .service import NhentaiService, get_nhentai_service

router = APIRouter()
SERVICE_DEP = Annotated[NhentaiService, Depends(get_nhentai_service)]
HEADER_DEP = Annotated[dict, Depends(require_telegram_headers)]


@router.get("/random", response_model=AlbumResponse, summary="Get a random gallery")
async def get_random(service: SERVICE_DEP, headers: HEADER_DEP):
    chat_id = int(headers["chat_id"])
    gallery = await service.get_random_gallery()
    return await service.prepare_album_response(gallery, chat_id)


@router.get(
    "/gallery/{gallery_id}",
    response_model=AlbumResponse,
    summary="Get a specific gallery by ID",
)
async def get_gallery_by_id(gallery_id: int, service: SERVICE_DEP, headers: HEADER_DEP):
    chat_id = int(headers["chat_id"])
    gallery = await service.get_gallery(gallery_id)
    return await service.prepare_album_response(gallery, chat_id)
