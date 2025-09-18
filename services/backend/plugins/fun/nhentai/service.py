import platform
import random
import ssl
from datetime import datetime
from typing import Annotated

import httpx
from fastapi import Depends
from plugins.core.config.service import ConfigService, get_config_service
from structlog import get_logger
from utils.exceptions import NotFoundError, ServiceError

from .models import AlbumResponse, NhentaiGallery, Tag, Title, Images

log = get_logger(__name__)


HEADERS_FIREFOX = {
    "User-Agent": f"Mozilla/5.0 ({platform.system()} NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
CIPHERS_FIREFOX = (
    "TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
)


class NhentaiService:
    BASE_URL = "https://nhentai.net"
    IMAGE_URL_TEMPLATE = "https://i.nhentai.net/galleries/{media_id}/{page_num}.{ext}"
    THUMB_URL_TEMPLATE = "https://t.nhentai.net/galleries/{media_id}/thumb.{ext}"
    COVER_URL_TEMPLATE = "https://t.nhentai.net/galleries/{media_id}/cover.{ext}"
    MAX_RANDOM_ID = 550000

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self._client = self._create_httpx_client()

    def _create_httpx_client(self) -> httpx.AsyncClient:
        ssl_context = ssl.create_default_context()
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
        ssl_context.set_ciphers(CIPHERS_FIREFOX)
        return httpx.AsyncClient(
            headers=HEADERS_FIREFOX, verify=ssl_context, timeout=20.0, http2=True
        )

    async def _make_request(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = await self._client.get(url, params=params)
            if response.status_code == 404:
                raise NotFoundError(f"Gallery not found at endpoint: {endpoint}")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            log.error("Nhentai request failed", url=str(e.request.url), error=str(e))
            raise ServiceError("Failed to connect to nhentai.net.") from e

    def _parse_gallery_data(self, data: dict) -> NhentaiGallery:
        ext_map = {"j": "jpg", "p": "png", "g": "gif"}

        def get_page_url(page_num, page_data):
            ext = ext_map.get(page_data["t"], "jpg")
            return self.IMAGE_URL_TEMPLATE.format(
                media_id=data["media_id"], page_num=page_num, ext=ext
            )

        cover_ext = ext_map.get(data["images"]["cover"]["t"], "jpg")
        thumb_ext = ext_map.get(data["images"]["thumbnail"]["t"], "jpg")

        return NhentaiGallery(
            id=data["id"],
            media_id=data["media_id"],
            title=Title(**data["title"]),
            images=Images(
                pages=[
                    get_page_url(i + 1, p)
                    for i, p in enumerate(data["images"]["pages"])
                ],
                cover=self.COVER_URL_TEMPLATE.format(
                    media_id=data["media_id"], ext=cover_ext
                ),
                thumbnail=self.THUMB_URL_TEMPLATE.format(
                    media_id=data["media_id"], ext=thumb_ext
                ),
            ),
            scanlator=data.get("scanlator", ""),
            upload_date=data["upload_date"],
            tags=[Tag(**tag) for tag in data["tags"]],
            num_pages=data["num_pages"],
            num_favorites=data["num_favorites"],
        )

    async def get_gallery(self, gallery_id: int) -> NhentaiGallery:
        data = await self._make_request(f"api/gallery/{gallery_id}")
        return self._parse_gallery_data(data)

    async def get_random_gallery(self) -> NhentaiGallery:
        for _ in range(10):
            random_id = random.randint(1, self.MAX_RANDOM_ID)
            try:
                return await self.get_gallery(random_id)
            except NotFoundError:
                log.warning("Random nhentai ID not found, retrying", id=random_id)
                continue
        raise NotFoundError(
            "Could not find a valid random gallery after multiple attempts."
        )

    async def prepare_album_response(
        self, gallery: NhentaiGallery, chat_id: int
    ) -> AlbumResponse:
        blacklist = await self.config_service.get(
            f"fun/nhentai.blacklist_tags.{chat_id}", default=[]
        )
        should_blur = await self.config_service.get(
            f"fun/nhentai.blur_enabled.{chat_id}", default=True
        )

        gallery_tags = {tag.name for tag in gallery.tags}
        has_blacklisted_tag = any(tag in gallery_tags for tag in blacklist)

        link = f"https://nhentai.net/g/{gallery.id}"
        caption = f"<b>№{gallery.id}</b> | <a href='{link}'><b>{gallery.title.pretty}</b></a>\n\n"
        caption += f"<b>Pages:</b> {gallery.num_pages}\n<b>Favorites:</b> {gallery.num_favorites}\n\n"

        tags_by_type = {}
        for tag in gallery.tags:
            tags_by_type.setdefault(tag.type, []).append(tag.name)

        for tag_type, tags in tags_by_type.items():
            caption += f"<b>{tag_type.capitalize()}:</b> {', '.join(tags)}\n"

        upload_dt = datetime.fromtimestamp(gallery.upload_date)
        caption += f"\n<b>Uploaded:</b> {upload_dt.strftime('%Y-%m-%d')}"

        total_pages = gallery.num_pages
        sample_indices = {0}
        for p in [0.15, 0.30, 0.50, 0.70, 0.90]:
            if len(sample_indices) < 10:
                sample_indices.add(min(total_pages - 1, int(total_pages * p)))

        image_urls = [gallery.images.pages[i] for i in sorted(list(sample_indices))]

        return AlbumResponse(
            caption=caption,
            image_urls=image_urls,
            blur_images=(has_blacklisted_tag and should_blur),
        )


def get_nhentai_service(
    config_service: Annotated[ConfigService, Depends(get_config_service)],
) -> NhentaiService:
    return NhentaiService(config_service)
