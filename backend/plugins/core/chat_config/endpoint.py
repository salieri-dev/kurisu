"""Chat configuration API endpoints."""

from fastapi import APIRouter, Depends
from plugins.core.chat_config import service as config_service
from plugins.core.chat_config.models import (
    AllChatConfigsResponse,
    ChatConfig,
    ChatConfigGetResponse,
    ChatConfigSetRequest,
)
from structlog import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/set",
    response_model=ChatConfig,
    summary="Set a chat configuration parameter",
    description="Creates or updates a specific configuration parameter for a given chat.",
)
async def set_chat_config(
    request: ChatConfigSetRequest,
    service: config_service.ChatConfigService = Depends(
        config_service.get_chat_config_service
    ),
):
    """
    Sets a configuration value for a chat.
    Exceptions are handled by the global exception handler.
    """
    return await service.set_config(
        request.chat_id, request.param_name, request.param_value
    )


@router.get(
    "/{chat_id}",
    response_model=AllChatConfigsResponse,
    summary="Get all configuration parameters for a chat",
    description="Retrieves all key-value configuration pairs for a given chat.",
)
async def get_all_chat_configs(
    chat_id: int,
    service: config_service.ChatConfigService = Depends(
        config_service.get_chat_config_service
    ),
):
    """
    Retrieves all configuration values for a chat.
    Exceptions are handled by the global exception handler.
    """
    configs = await service.get_all_configs_for_chat(chat_id)
    return AllChatConfigsResponse(chat_id=chat_id, configs=configs)


@router.get(
    "/{chat_id}/{param_name}",
    response_model=ChatConfigGetResponse,
    summary="Get a chat configuration parameter",
    description="Retrieves the value of a specific configuration parameter for a given chat.",
)
async def get_chat_config(
    chat_id: int,
    param_name: str,
    service: config_service.ChatConfigService = Depends(
        config_service.get_chat_config_service
    ),
):
    """
    Retrieves a specific configuration value for a chat. If the parameter is not set,
    the `param_value` will be `null`.
    Exceptions are handled by the global exception handler.
    """
    config = await service.get_config(chat_id, param_name)
    if config:
        return ChatConfigGetResponse(
            chat_id=config.chat_id,
            param_name=config.param_name,
            param_value=config.param_value,
        )

    return ChatConfigGetResponse(chat_id=chat_id, param_name=param_name)
