import os
import random

from utils.exceptions import NotFoundError


class AltGirlsRepository:
    """Handles data access for altgirls images from the filesystem."""

    def __init__(self, assets_path: str):
        self.assets_path = assets_path
        if not os.path.isdir(self.assets_path):
            raise FileNotFoundError(
                f"Assets directory not found at: {self.assets_path}"
            )

    def get_random_image_paths(self, count: int) -> list[str]:
        """Scans the assets directory and returns a list of random image file paths."""
        images = []
        for root, _, files in os.walk(self.assets_path):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    images.append(os.path.join(root, file))

        if not images:
            raise NotFoundError("No images found in assets directory")

        return random.sample(images, min(count, len(images)))


def get_altgirls_repository() -> AltGirlsRepository:
    return AltGirlsRepository(assets_path="assets/woman")
