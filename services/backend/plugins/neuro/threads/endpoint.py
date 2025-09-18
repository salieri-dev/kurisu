from typing import Annotated

from fastapi import APIRouter, Depends
from utils.dependencies import require_telegram_headers

from .models import ThreadRequest, ThreadResponse
from .service import ThreadsService, get_threads_service

router = APIRouter()


SERVICE_DEPENDENCY = Depends(get_threads_service)
HEADERS_DEPENDENCY = Depends(require_telegram_headers)


async def _generate(
    thread_type: str,
    request: ThreadRequest,
    service: ThreadsService,
    headers: dict,
):
    """Common logic for both endpoints."""
    user_id = int(headers["user_id"])
    chat_id = int(headers["chat_id"])

    return await service.generate_thread(
        thread_type=thread_type,
        topic=request.topic,
        user_id=user_id,
        chat_id=chat_id,
    )


@router.post(
    "/bugurt",
    response_model=ThreadResponse,
    summary="Generate a 2ch-style Bugurt thread",
)
async def generate_bugurt_thread(
    request: ThreadRequest,
    service: Annotated[ThreadsService, SERVICE_DEPENDENCY],
    headers: dict = HEADERS_DEPENDENCY,
):
    return await _generate("bugurt", request, service, headers)


@router.post(
    "/greentext",
    response_model=ThreadResponse,
    summary="Generate a 4chan-style Greentext thread",
)
async def generate_greentext_thread(
    request: ThreadRequest,
    service: Annotated[ThreadsService, SERVICE_DEPENDENCY],
    headers: dict = HEADERS_DEPENDENCY,
):
    return await _generate("greentext", request, service, headers)
