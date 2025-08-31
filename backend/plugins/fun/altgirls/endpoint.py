from typing import Annotated

from fastapi import APIRouter, Depends, Query

from .models import AltGirlsResponse
from .service import AltGirlsService, get_altgirls_service

router = APIRouter()


@router.get(
    "",
    response_model=AltGirlsResponse,
    summary="Get random altgirls images",
    description=(
        "Retrieve random altgirls images with base64 encoding and source links."
    ),
)
def get_altgirls(
    service: Annotated[AltGirlsService, Depends(get_altgirls_service)],
    n: int = Query(1, description="Number of images to retrieve", ge=1, le=10),
):
    """
    Get random altgirls images.

    - **n**: Number of images to retrieve (1-10)
    - Returns an array of images with base64 data, filenames, and source links.
    - Errors like 'Not Found' are handled by the global exception handler.
    """
    result = service.get_altgirls_images(n)
    return AltGirlsResponse(**result)
