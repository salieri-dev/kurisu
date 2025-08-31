# backend/plugins/core/config/endpoint.py
import json
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from .models import ConfigGetResponse, SetConfigRequest
from .service import ConfigService, get_config_service

router = APIRouter()

# --- NEW ENDPOINT ---
@router.get(
    "/resolve/{key:path}",
    response_model=dict,
    summary="Resolve a configuration value (get or create)",
    description="Fetches a configuration value. If the key does not exist, it will be created with the provided default value."
)
async def resolve_config(
    key: str,
    service: Annotated[ConfigService, Depends(get_config_service)],
    default: str = Query(..., description="JSON-encoded default value to use if the key is not found."),
    description: str | None = Query(None, description="A description to set if the key is created.")
):
    try:
        default_value = json.loads(default)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="The 'default' query parameter must be a valid JSON string.")

    value = await service.get_or_create(key, default_value, description)
    return {"key": key, "value": value}
# --- END NEW ENDPOINT ---

@router.post(
    "",
    response_model=ConfigGetResponse,
    summary="Create or update a configuration",
    description="Sets a specific configuration key to a given value. This action is idempotent."
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
    description="Retrieves a full configuration item, including its value, description, and metadata."
)
async def get_config(
    key: str,
    service: Annotated[ConfigService, Depends(get_config_service)],
):
    config_item = await service.get_full_config_item(key)
    if not config_item:
        raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")
    return config_item