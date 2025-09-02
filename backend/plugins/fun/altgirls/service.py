import base64
import os
from typing import Annotated, Any

from fastapi import Depends
from utils.asset_service import AssetService, get_asset_service
from utils.exceptions import NotFoundError


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
    """Service layer for altgirls business logic, using the abstract AssetService."""

    ASSET_CATEGORY = "fun/altgirls/assets"

    def __init__(self, asset_service: AssetService):
        self.asset_service = asset_service

    def get_altgirls_images(self, count: int) -> dict[str, Any]:
        """
        Retrieves random altgirls images by coordinating with the AssetService
        and applying business logic (encoding, mapping).
        """
        try:
            # Use the central asset service to get asset details
            assets = self.asset_service.get_random_assets(self.ASSET_CATEGORY, count)
        except NotFoundError as e:
            # Re-raise to be handled by the global exception handler
            raise e

        images_data = []
        for asset in assets:
            images_data.append(
                {
                    "filename": asset.filename,
                    "base64_data": encode_image_to_base64(str(asset.path)),
                    "source_link": get_image_owner_mapping(str(asset.path)),
                }
            )

        return {"images": images_data, "count": len(images_data)}


def get_altgirls_service(
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> AltGirlsService:
    """Dependency provider for the AltGirlsService."""
    return AltGirlsService(asset_service)
