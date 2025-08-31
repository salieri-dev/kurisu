"""API endpoints for the Instagram plugin."""

from fastapi import APIRouter, HTTPException
from plugins.utilities.instagram.models import InstagramMediaResponse
from plugins.utilities.instagram.service import get_instagram_service
from structlog import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/{media_code}",
    response_model=InstagramMediaResponse,
    summary="Fetch Instagram Media",
    description="Fetches media content (photos, videos, and metadata) from an Instagram post using its shortcode.",
)
async def get_instagram_media(media_code: str):
    """
    Retrieves Instagram media by its shortcode.

    - **media_code**: The 11-character code from the Instagram URL (e.g., CqX-...).
    """
    service = get_instagram_service()
    try:
        media = await service.get_instagram_media(media_code)
        return InstagramMediaResponse(media=media)
    except ValueError as e:
        logger.warning(
            "Invalid request for Instagram media", media_code=media_code, error=str(e)
        )
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        logger.error(
            "Failed to connect to Instagram API", media_code=media_code, error=str(e)
        )
        raise HTTPException(
            status_code=502, detail=f"Could not fetch data from Instagram: {e}"
        )
    except Exception:
        logger.exception(
            "An unexpected error occurred in Instagram endpoint", media_code=media_code
        )
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        )
