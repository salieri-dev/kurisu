# path: backend/plugins/neuro/summary/endpoint.py

from typing import Annotated
from fastapi import APIRouter, Depends

from utils.dependencies import require_telegram_headers
from .models import SummaryRequest, SummaryResponse
from .service import SummaryService, get_summary_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=SummaryResponse,
    summary="Generate and Store a Chat Summary",
    description="Generates a daily summary for a specific chat, stores it in the database, and returns the formatted text.",
)
async def generate_summary_endpoint(
    request: SummaryRequest,
    service: Annotated[SummaryService, Depends(get_summary_service)],
    # require_telegram_headers is not strictly needed here as the bot job is the primary user,
    # but it's good practice for manual triggers and logging context.
    headers: Annotated[dict, Depends(require_telegram_headers)],
):
    """
    Handles the request from the bot to generate a summary for a given chat and date.
    The core logic is delegated entirely to the SummaryService.
    """
    return await service.generate_summary(
        request.chat_id, request.chat_title, request.date
    )
