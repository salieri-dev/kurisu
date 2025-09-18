import json
from typing import Any, List

import httpx
from config import settings


class BackendClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=str(settings.backend_url),
            headers={"X-API-Key": settings.api_key},
            timeout=15.0,
        )

    async def get_all_configs(self) -> List[dict]:
        response = await self._client.get("/core/config")
        response.raise_for_status()
        return response.json()

    async def set_config(self, key: str, value: Any, description: str):
        try:
            value_parsed = json.loads(value)
        except json.JSONDecodeError:
            value_parsed = value

        payload = {"key": key, "value": value_parsed, "description": description}
        response = await self._client.post("/core/config", json=payload)
        response.raise_for_status()
        return response.json()

    async def clear_cache(self, key: str):
        response = await self._client.delete(f"/core/config/cache/{key}")
        response.raise_for_status()


client = BackendClient()
