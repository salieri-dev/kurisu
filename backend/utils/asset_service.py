import mimetypes
import random
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel
from utils.exceptions import NotFoundError


class AssetDetail(BaseModel):
    """A structured model representing a single asset."""

    path: Path
    filename: str
    size_bytes: int
    content_type: str | None


class AssetService(Protocol):
    """
    A protocol defining the contract for any asset storage service.
    This allows for interchangeable implementations (local, S3, etc.).
    """

    def get_random_assets(self, category: str, count: int) -> list[AssetDetail]:
        """
        Retrieves a specified number of random assets from a given category.

        Args:
            category: The sub-path or key prefix for the asset group (e.g., 'fun/altgirls/assets').
            count: The number of random assets to retrieve.

        Returns:
            A list of AssetDetail objects.

        Raises:
            NotFoundError: If the category does not exist or contains no valid assets.
        """
        ...


class LocalAssetService:
    """An implementation of AssetService that reads from the local filesystem."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        if not self.base_path.is_dir():
            raise FileNotFoundError(f"Asset base path not found: {self.base_path}")

    def get_random_assets(self, category: str, count: int) -> list[AssetDetail]:
        category_path = self.base_path / category
        if not category_path.is_dir():
            raise NotFoundError(f"Asset category '{category}' not found.")

        # Use rglob for recursive search, more modern than os.walk
        all_files = [
            p
            for p in category_path.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        ]

        if not all_files:
            raise NotFoundError(f"No assets found in category '{category}'.")

        # Ensure we don't request more samples than available
        num_to_sample = min(count, len(all_files))
        selected_paths = random.sample(all_files, num_to_sample)

        asset_details = []
        for path in selected_paths:
            content_type, _ = mimetypes.guess_type(path)
            asset_details.append(
                AssetDetail(
                    path=path,
                    filename=path.name,
                    size_bytes=path.stat().st_size,
                    content_type=content_type,
                )
            )

        return asset_details


# --- Dependency Injection ---

_asset_service_instance = None


def get_asset_service() -> AssetService:
    """
    FastAPI dependency provider for the AssetService.
    Uses a singleton pattern to instantiate the service once.
    """
    global _asset_service_instance
    if _asset_service_instance is None:
        # The base path is the 'plugins' directory inside 'backend'
        base_plugins_path = Path(__file__).parent.parent / "plugins"
        _asset_service_instance = LocalAssetService(base_path=base_plugins_path)
    return _asset_service_instance
