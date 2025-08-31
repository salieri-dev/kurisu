"""GDPR API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from plugins.core.gdpr import service as gdpr_service
from plugins.core.gdpr.models import GDPRDeleteRequest, GDPRDeleteResponse

router = APIRouter()


@router.delete(
    "/users/{user_id}",
    response_model=GDPRDeleteResponse,
    summary="Delete all user data (GDPR compliance)",
    description=(
        "Delete all data associated with a specific user ID for GDPR compliance."
    ),
)
async def delete_user_data(
    user_id: int,
    service: Annotated[
        gdpr_service.GDPRService, Depends(gdpr_service.get_gdpr_service)
    ],
) -> GDPRDeleteResponse:
    """
    Delete all data for a specific user (GDPR compliance).
    """

    request = GDPRDeleteRequest(user_id=user_id)
    result = await service.delete_user_data(request)
    return result
