import json
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query

from .models import ConfigGetResponse, SetConfigRequest
from .service import ConfigService, get_config_service

router = APIRouter()


@router.get(
    "/resolve/{key:path}",
    response_model=dict,
    summary="Resolve a configuration value (get or create)",
    description="Fetches a configuration value. If the key does not exist, it will be created with the provided default value.",
)
async def resolve_config(
    key: str,
    service: Annotated[ConfigService, Depends(get_config_service)],
    default: str = Query(
        ..., description="JSON-encoded default value to use if the key is not found."
    ),
    description: str | None = Query(
        None, description="A description to set if the key is created."
    ),
):
    try:
        default_value = json.loads(default)
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=400,
            detail="The 'default' query parameter must be a valid JSON string.",
        ) from err

    value = await service.get_or_create(key, default_value, description)
    return {"key": key, "value": value}


@router.post(
    "",
    response_model=ConfigGetResponse,
    summary="Create or update a configuration",
    description="Sets a specific configuration key to a given value. This action is idempotent.",
)
async def set_config(
    request: SetConfigRequest,
    service: Annotated[ConfigService, Depends(get_config_service)],
):
    return await service.set(request)


@router.get(
    "/{key:path}",
    response_model=ConfigGetResponse,
    summary="Get a configuration item",
    description="Retrieves a full configuration item, including its value, description, and metadata.",
)
async def get_config(
    key: str,
    service: Annotated[ConfigService, Depends(get_config_service)],
):
    config_item = await service.get_full_config_item(key)
    if not config_item:
        raise HTTPException(
            status_code=404, detail=f"Configuration key '{key}' not found"
        )
    return config_item


@router.get(
    "",
    response_model=List[ConfigGetResponse],
    summary="Get all configuration items",
    description="Retrieves a list of all configuration items from the database. Intended for dashboard use.",
)
async def get_all_configs(
    service: Annotated[ConfigService, Depends(get_config_service)],
):
    return await service.get_all_configs()


@router.delete(
    "/cache/{key:path}",
    status_code=204,
    summary="Clear cache for a configuration key",
    description="Removes a specific configuration key from the Redis cache, forcing a reload from the database on the next request.",
)
async def clear_config_cache(
    key: str,
    service: Annotated[ConfigService, Depends(get_config_service)],
):
    await service.clear_cache_for_key(key)
    return None
