from pydantic import BaseModel, HttpUrl
from typing import List, Optional


class Title(BaseModel):
    english: Optional[str] = None
    japanese: Optional[str] = None
    pretty: Optional[str] = None


class Tag(BaseModel):
    id: int
    type: str
    name: str
    url: str
    count: int


class Images(BaseModel):
    pages: List[HttpUrl]
    cover: HttpUrl
    thumbnail: HttpUrl


class NhentaiGallery(BaseModel):
    id: int
    media_id: int
    title: Title
    images: Images
    scanlator: Optional[str] = None
    upload_date: int
    tags: List[Tag]
    num_pages: int
    num_favorites: int


class AlbumResponse(BaseModel):
    """Response for a single gallery request, containing everything the bot needs."""

    caption: str
    image_urls: List[HttpUrl]
    blur_images: bool
