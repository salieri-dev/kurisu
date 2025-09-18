from typing import Annotated

from fastapi import APIRouter, Depends
from utils.dependencies import require_telegram_headers

from .models import IdeogramRequest, IdeogramResponse
from .service import IdeogramService, get_ideogram_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=IdeogramResponse,
    summary="Generate images with Ideogram",
)
async def generate_ideogram_endpoint(
    request: IdeogramRequest,
    service: Annotated[IdeogramService, Depends(get_ideogram_service)],
    headers: Annotated[dict, Depends(require_telegram_headers)],
):
    user_id = int(headers["user_id"])
    chat_id = int(headers["chat_id"])
    return await service.generate(
        request.prompt, user_id, chat_id, request.negative_prompt
    )
