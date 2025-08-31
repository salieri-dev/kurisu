# bot/utils/config_client.py
import json
from typing import Any
import structlog
from pyrogram.types import Message
from .api_client import backend_client
from .exceptions import APIError

log = structlog.get_logger(__name__)

async def get_config(key: str, message: Message, default: Any = None, description: str | None = None) -> Any:
    """
    Fetches a configuration value from the backend using the 'resolve' endpoint.

    If the key does not exist on the backend, it will be created using the
    provided default value and description.
    """
    try:
        # JSON-encode the default value to preserve its type over HTTP query params
        default_json = json.dumps(default)
        params = {"default": default_json}
        if description:
            params["description"] = description
            
        response = await backend_client.get(
            f"/core/config/resolve/{key}",
            message=message,
            params=params
        )

        # The resolve endpoint now guarantees a 'value' key in the response
        return response.get('value', default)

    except APIError as e:
        # A 404 should no longer happen. This now only catches server errors.
        log.error(
            "API error resolving config, using local default",
            key=key,
            status_code=e.status_code,
            detail=e.detail,
            correlation_id=e.correlation_id,
        )
        return default
    except Exception as e:
        log.error(
            "Unhandled error resolving config, using local default",
            key=key, error=str(e), exc_info=True
        )
        return default