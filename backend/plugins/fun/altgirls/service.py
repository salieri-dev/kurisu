import base64
import os
from typing import Annotated, Any

from fastapi import Depends
from utils.exceptions import NotFoundError

from .repository import AltGirlsRepository, get_altgirls_repository


def get_image_owner_mapping(image_path: str) -> str:
    """Extracts the platform and username from the directory name."""
    dir_name = os.path.basename(os.path.dirname(image_path))
    if "_" not in dir_name:
        return "Unknown source"

    platform, username = dir_name.split("_", 1)
    if platform == "tg":
        return f"https://t.me/{username}"
    elif platform == "vk":
        return f"https://vk.com/{username}"
    else:
        return "Unknown source"


def encode_image_to_base64(image_path: str) -> str:
    """Converts an image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


class AltGirlsService:
    """Service layer for altgirls business logic."""

    def __init__(self, repository: AltGirlsRepository):
        self.repository = repository

    def get_altgirls_images(self, count: int) -> dict[str, Any]:
        """
        Retrieves random altgirls images by coordinating with the repository
        and applying business logic (encoding, mapping).
        """
        try:
            image_paths = self.repository.get_random_image_paths(count)
        except NotFoundError as e:
            raise e

        images_data = []
        for image_path in image_paths:
            images_data.append(
                {
                    "filename": os.path.basename(image_path),
                    "base64_data": encode_image_to_base64(image_path),
                    "source_link": get_image_owner_mapping(image_path),
                }
            )

        return {"images": images_data, "count": len(images_data)}


def get_altgirls_service(
    repository: Annotated[AltGirlsRepository, Depends(get_altgirls_repository)],
) -> AltGirlsService:
    return AltGirlsService(repository)
