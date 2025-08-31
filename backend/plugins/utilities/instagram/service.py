"""Service layer for fetching Instagram media."""

import re
from datetime import UTC, datetime
from typing import Any, Optional

import httpx
from config import AppConfig, settings
from plugins.utilities.instagram.models import InstagramMedia
from structlog import get_logger

logger = get_logger(__name__)


class InstagramService:
    """A class for fetching Instagram media data."""

    API_URL: str = "https://www.instagram.com/graphql/query"

    def __init__(self, config: AppConfig) -> None:
        """Initialize the InstagramService with a validated configuration object."""
        self.headers: dict[str, str] = config.instagram_headers_json
        self.cookies: dict[str, str] = config.instagram_cookies_json
        self.payload: dict[str, Any] = config.instagram_payload_json

        self.proxy_enabled = config.proxy_enabled
        self.proxy_host = config.proxy_host
        self.proxy_port = config.proxy_port

    async def get_instagram_media(self, media_id: str) -> InstagramMedia:
        """
        Fetch and parse Instagram media data for a given media_id.
        """
        media_id_pattern = r"^[A-Za-z0-9_-]{7,39}$"
        if not re.match(media_id_pattern, media_id):
            raise ValueError(f"Invalid media_id format: {media_id}")

        self.payload["variables"]["shortcode"] = media_id

        client_kwargs = {
            "headers": self.headers,
            "cookies": self.cookies,
            "timeout": httpx.Timeout(60.0, connect=15.0),
        }

        if self.proxy_enabled and self.proxy_host and self.proxy_port:
            client_kwargs["proxy"] = f"socks5://{self.proxy_host}:{self.proxy_port}"

        logger.info("Attempting to fetch Instagram media", media_id=media_id)
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(self.API_URL, json=self.payload)
                response.raise_for_status()
                json_data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error fetching Instagram media",
                media_id=media_id,
                status_code=e.response.status_code,
                response_text=e.response.text,
                exc_info=True,
            )
            raise ConnectionError(
                f"Failed to fetch from Instagram: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(
                "Generic error fetching Instagram media",
                media_id=media_id,
                error=str(e),
                exc_info=True,
            )
            raise ConnectionError(f"An unexpected error occurred: {str(e)}")

        return self._parse_media_json(json_data)

    def _parse_media_json(self, json_data: dict[str, Any]) -> InstagramMedia:
        """Parse the raw JSON response from Instagram into our Pydantic model."""
        items = (
            json_data.get("data", {})
            .get("xdt_api__v1__media__shortcode__web_info", {})
            .get("items")
        )
        if not items or not isinstance(items, list) or len(items) == 0:
            raise ValueError("Media not found or unexpected API response structure")

        media = items[0]
        owner = media.get("owner", {})
        caption_node = media.get("caption")
        caption_text = (
            caption_node.get("text") if isinstance(caption_node, dict) else None
        )

        return InstagramMedia(
            id=media.get("code"),
            attachments=self._extract_candidates(media),
            published_at=datetime.fromtimestamp(media.get("taken_at", 0), UTC),
            source_url=f"https://www.instagram.com/p/{media.get('code')}",
            tags=self._get_tags_from_caption(caption_text),
            author_id=owner.get("id"),
            author_name=owner.get("username"),
            author_url=f"https://www.instagram.com/{owner.get('username', '')}",
            description=caption_text,
            views=media.get("view_count"),
            likes=media.get("like_count"),
            title=media.get("title"),
            comments=media.get("comment_count"),
        )

    def _extract_candidates(self, media: dict[str, Any]) -> list[str]:
        """Extract all media attachment URLs from the post."""
        candidates = []
        if "carousel_media" in media and media["carousel_media"]:
            for item in media["carousel_media"]:
                if url := self._get_best_resolution_url(item):
                    candidates.append(url)
        else:
            if url := self._get_best_resolution_url(media):
                candidates.append(url)
        return candidates

    def _get_best_resolution_url(self, item: dict[str, Any]) -> Optional[str]:
        """Get the best resolution URL from a single media item (photo or video)."""
        if "video_versions" in item and item["video_versions"]:
            return self._extract_max_resolution_url(item.get("video_versions", []))
        if "image_versions2" in item:
            return self._extract_max_resolution_url(
                item.get("image_versions2", {}).get("candidates", [])
            )
        return None

    def _extract_max_resolution_url(
        self, candidates: list[dict[str, Any]]
    ) -> Optional[str]:
        """Find the URL with the highest resolution from a list of candidates."""
        valid_candidates = [
            c
            for c in candidates
            if isinstance(c, dict) and "width" in c and "height" in c and "url" in c
        ]
        if not valid_candidates:
            return None
        max_res = max(valid_candidates, key=lambda x: x["width"] * x["height"])
        return max_res["url"]

    def _get_tags_from_caption(self, caption: Optional[str]) -> list[str]:
        """Extract hashtags from the caption text."""
        if not caption:
            return []
        return [tag.strip() for tag in re.findall(r"#(\w+)", caption)]


def get_instagram_service() -> InstagramService:
    """Dependency provider for the InstagramService."""
    return InstagramService(config=settings)
