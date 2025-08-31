"""Pydantic models for the Instagram plugin."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class InstagramMedia(BaseModel):
    """Represents a single Instagram media post."""

    id: str
    source: str = "Instagram"
    attachments: list[HttpUrl]
    published_at: datetime
    source_url: Optional[HttpUrl] = None
    tags: list[str] = Field(default_factory=list)
    title: Optional[str] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_url: Optional[HttpUrl] = None
    description: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None


class InstagramMediaResponse(BaseModel):
    """API response model for an Instagram media request."""

    status: str = "success"
    media: InstagramMedia

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "media": {
                    "id": "CqX...-",
                    "source": "Instagram",
                    "attachments": ["https://scontent.cdninstagram.com/.../3.jpg"],
                    "published_at": "2023-03-27T12:00:00Z",
                    "source_url": "https://www.instagram.com/p/CqX...-/",
                    "author_name": "instagram",
                    "description": "A sample description.",
                    "likes": 12345,
                    "comments": 678,
                },
            }
        }
