"""Pydantic models for altgirls plugin API responses."""

from pydantic import BaseModel, ConfigDict


class ImageData(BaseModel):
    """Model for individual image data."""

    filename: str
    base64_data: str
    source_link: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "filename": "image.jpg",
                    "base64_data": "/9j/4AAQSkZJRgABAQAAAQ...",
                    "source_link": "[username](https://t.me/username)",
                }
            ]
        }
    )


class AltGirlsResponse(BaseModel):
    """Response model for altgirls endpoint."""

    images: list[ImageData]
    count: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "images": [
                        {
                            "filename": "image1.jpg",
                            "base64_data": "/9j/4AAQSkZJRgABAQAAAQ...",
                            "source_link": "[username](https://t.me/username)",
                        }
                    ],
                    "count": 1,
                }
            ]
        }
    )
