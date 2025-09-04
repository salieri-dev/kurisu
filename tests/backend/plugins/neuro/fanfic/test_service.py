
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.plugins.neuro.fanfic.models import LLMFanficResponse
from backend.plugins.neuro.fanfic.service import FanficService
from unittest.mock import ANY


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Provides a mock for the LLMClient."""
    return AsyncMock()

@pytest.fixture
def mock_fal_client() -> AsyncMock:
    """Provides a mock for the FalAIClient."""
    return AsyncMock()

@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provides a mock for the FanficRepository."""
    return AsyncMock()

@pytest.fixture
def mock_config_service() -> AsyncMock:
    """Provides a mock for the ConfigService."""
    mock = MagicMock()
    mock.get_or_create = AsyncMock(side_effect=lambda key, default, *args: default)
    return mock


@pytest.fixture
def fanfic_service(
    mock_llm_client: AsyncMock,
    mock_fal_client: AsyncMock,
    mock_repository: AsyncMock,
    mock_config_service: AsyncMock,
) -> FanficService:
    """
    Provides an instance of FanficService with all its dependencies mocked.
    Pytest automatically discovers and injects the other fixtures defined above.
    """
    return FanficService(
        llm_client=mock_llm_client,
        fal_client=mock_fal_client,
        repository=mock_repository,
        config=mock_config_service,
    )


@pytest.mark.asyncio
async def test_generate_fanfic_happy_path(
    fanfic_service: FanficService,
    mock_llm_client: AsyncMock,
    mock_fal_client: AsyncMock,
    mock_repository: AsyncMock,
):
    """
    Tests the entire orchestration logic of the generate_fanfic method.
    """
    fake_user_id = 123
    fake_chat_id = 456
    fake_topic = "testing the service"
    
    fake_llm_response = LLMFanficResponse(
        title="Test Fanfic Title",
        content="This is the story content.",
        image_prompt="A beautiful, detailed image prompt.",
    )
    mock_llm_client.structured_chat_completion.return_value = fake_llm_response

    fake_image_url = "http://fake.url/image.png"
    mock_fal_client.generate_image.return_value = fake_image_url

    mock_repository.save_fanfic.return_value = "fake_db_id_12345"

    result = await fanfic_service.generate_fanfic(
        topic=fake_topic,
        user_id=fake_user_id,
        chat_id=fake_chat_id,
    )

    assert result.title == fake_llm_response.title
    assert result.content == fake_llm_response.content
    assert result.image_url == fake_image_url

    mock_llm_client.structured_chat_completion.assert_awaited_once_with(
        ANY,
        "anthropic/claude-3.5-sonnet",
        response_model=LLMFanficResponse
    )

    expected_payload = {
        "prompt": "A beautiful, detailed image prompt.",
        "image_size": "landscape_4_3",
        "num_images": 1,
    }
    mock_fal_client.generate_image.assert_awaited_once_with(
        "fal-ai/flux/dev",
        expected_payload
    )

    mock_repository.save_fanfic.assert_awaited_once()
    saved_data = mock_repository.save_fanfic.call_args.args[0]
    assert saved_data.user_id == fake_user_id
    assert saved_data.chat_id == fake_chat_id
    assert saved_data.topic == fake_topic
    assert saved_data.title == fake_llm_response.title
    assert saved_data.image_url == fake_image_url