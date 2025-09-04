from typing import Annotated

from fastapi import APIRouter, Depends
from utils.dependencies import require_telegram_headers

from .models import FanficRequest, FanficResponse
from .service import FanficService, get_fanfic_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=FanficResponse,
    summary="Generate a Fanfic with an Image",
)
async def generate_fanfic_endpoint(
    request: FanficRequest,
    service: Annotated[FanficService, Depends(get_fanfic_service)],
    headers: Annotated[dict, Depends(require_telegram_headers)],
):
    user_id = int(headers["user_id"])
    chat_id = int(headers["chat_id"])
    return await service.generate_fanfic(request.topic, user_id, chat_id)
