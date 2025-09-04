import base64
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.plugins.fun.altgirls.service import AltGirlsService
from backend.utils.asset_service import AssetDetail
from backend.utils.exceptions import NotFoundError


@pytest.fixture
def altgirls_service() -> AltGirlsService:
    """
    Provides an instance of AltGirlsService with a mocked AssetService.
    The mock is a MagicMock, a powerful fake object that we can control.
    """
    mock_asset_service = MagicMock()
    service = AltGirlsService(asset_service=mock_asset_service)
    return service


def test_get_altgirls_images_happy_path(
    tmp_path: Path, altgirls_service: AltGirlsService
):
    """
    Tests the successful case where the AssetService returns valid image details.

    Args:
        tmp_path: A pytest fixture that provides a temporary directory for file operations.
        altgirls_service: Our fixture that provides the service with a mocked dependency.
    """
    fake_image_content = b"fake image data"
    fake_image_path = tmp_path / "tg_testuser" / "test.jpg"
    fake_image_path.parent.mkdir()
    fake_image_path.write_bytes(fake_image_content)

    mock_asset_detail = AssetDetail(
        path=fake_image_path,
        filename="test.jpg",
        size_bytes=123,
        content_type="image/jpeg",
    )

    altgirls_service.asset_service.get_random_assets.return_value = [mock_asset_detail]

    result = altgirls_service.get_altgirls_images(count=1)

    assert "images" in result
    assert "count" in result
    assert result["count"] == 1
    assert len(result["images"]) == 1

    image_data = result["images"][0]
    expected_b64 = base64.b64encode(fake_image_content).decode("utf-8")

    assert image_data["filename"] == "test.jpg"
    assert image_data["base64_data"] == expected_b64
    assert image_data["source_link"] == "https://t.me/testuser"

    altgirls_service.asset_service.get_random_assets.assert_called_once_with(
        "fun/altgirls/assets", 1
    )


def test_get_altgirls_images_not_found(altgirls_service: AltGirlsService):
    """
    Tests the case where the AssetService finds no assets and raises a NotFoundError.
    We want to ensure our service correctly propagates this error.
    """
    altgirls_service.asset_service.get_random_assets.side_effect = NotFoundError(
        "No assets found"
    )

    with pytest.raises(NotFoundError, match="No assets found"):
        altgirls_service.get_altgirls_images(count=1)

    altgirls_service.asset_service.get_random_assets.assert_called_once_with(
        "fun/altgirls/assets", 1
    )
