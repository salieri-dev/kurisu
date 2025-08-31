"""Pydantic models for the Instagram plugin."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class InstagramMedia(BaseModel):
    """Represents a single Instagram media post."""

    id: str
    source: str = "Instagram"
    attachments: list[HttpUrl]
    published_at: datetime
    source_url: HttpUrl | None = None
    tags: list[str] = Field(default_factory=list)
    title: str | None = None
    author_id: str | None = None
    author_name: str | None = None
    author_url: HttpUrl | None = None
    description: str | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None


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
