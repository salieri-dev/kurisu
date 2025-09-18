from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends, Request
from .models import InstagramMediaResponse
from .service import InstagramService
from .config import InstagramSettings
from structlog import get_logger

router = APIRouter()
logger = get_logger(__name__)


def get_instagram_settings(request: Request) -> InstagramSettings:
    """
    Extracts and validates Instagram-specific settings from the global
    application settings object.
    """
    return InstagramSettings.model_validate(request.app.state.settings)


def get_instagram_service(
    config: Annotated[InstagramSettings, Depends(get_instagram_settings)],
) -> InstagramService:
    """Instantiates the InstagramService with its required configuration."""
    return InstagramService(config=config)


@router.get(
    "/{media_code}",
    response_model=InstagramMediaResponse,
    summary="Fetch Instagram Media",
    description=("Fetches media from an Instagram post using its shortcode."),
)
async def get_instagram_media(
    media_code: str,
    service: Annotated[InstagramService, Depends(get_instagram_service)],
):
    """
    Retrieves Instagram media by its shortcode.
    - **media_code**: The 11-character code from the Instagram URL (e.g., CqX-...).
    """
    try:
        media = await service.get_instagram_media(media_code)
        return InstagramMediaResponse(media=media)
    except ValueError as e:
        logger.warning(
            "Invalid request for Instagram media", media_code=media_code, error=str(e)
        )
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConnectionError as e:
        logger.error(
            "Failed to connect to Instagram API", media_code=media_code, error=str(e)
        )
        raise HTTPException(
            status_code=502, detail=f"Could not fetch data from Instagram: {e}"
        ) from e
    except Exception as e:
        logger.exception(
            "An unexpected error occurred in Instagram endpoint", media_code=media_code
        )
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        ) from e
