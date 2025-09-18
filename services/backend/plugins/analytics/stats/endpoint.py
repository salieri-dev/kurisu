from typing import Annotated
from fastapi import APIRouter, Depends
from .models import FullStatsResponse
from .service import StatsService, get_stats_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=FullStatsResponse,
    summary="Get comprehensive bot statistics",
)
async def get_summary_stats(
    service: Annotated[StatsService, Depends(get_stats_service)],
) -> FullStatsResponse:
    """
    Retrieves a full summary of bot usage statistics.
    This endpoint is protected by the global API key.
    """
    return await service.get_full_stats()
