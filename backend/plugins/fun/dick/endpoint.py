"""Dick generation API endpoints."""

import base64

from fastapi import APIRouter
from plugins.fun.dick import service as dick_service
from plugins.fun.dick.models import DickAttributes, ImageResponse

router = APIRouter()


@router.get(
    "/generate",
    response_model=DickAttributes,
    summary="Generate random dick attributes",
    description="Generate random, detailed attributes for a user's dick and return them as JSON.",
)
def generate_dick_attributes():
    """
    Generate random dick attributes.

    - Returns a JSON object with various dick attributes.
    """
    attributes = dick_service.calculate_dong_attributes()
    return DickAttributes(**attributes)


@router.post(
    "/image",
    response_model=ImageResponse,
    summary="Generate a dick image report",
    description="Generate a visual report of a user's dick attributes based on provided data.",
)
def get_dick_image(attributes: DickAttributes):
    """
    Generate a PNG image report of dick attributes.

    - **attributes**: JSON object containing dick attributes.
    - Returns a JSON response with a base64 encoded PNG image.
    """
    image_buffer = dick_service.plot_attributes(attributes.dict())
    image_bytes = image_buffer.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    return ImageResponse(image_base64=image_base64)
