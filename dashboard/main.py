import json

import httpx
import structlog
from config import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from kurisu_core.logging_config import setup_structlog

setup_structlog(json_logs=settings.json_logs)
logger = structlog.get_logger(__name__)

app = FastAPI(title="Kurisu Dashboard")

async def get_backend_client() -> httpx.AsyncClient:
    """Creates an httpx client to communicate with the backend."""
    return httpx.AsyncClient(
        base_url=str(settings.backend_url),
        headers={"X-API-Key": settings.api_key},
        timeout=15.0,
    )


@app.get("/api/configs")
async def proxy_get_all_configs():
    """Proxies the request to get all configurations from the backend."""
    try:
        async with await get_backend_client() as client:
            response = await client.get("/core/config")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Backend error getting configs", detail=e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
    except httpx.RequestError as e:
        logger.error("Network error getting configs", error=str(e))
        raise HTTPException(status_code=502, detail="Bad Gateway: Cannot connect to backend service.")

@app.post("/api/configs")
async def proxy_update_config(request: Request):
    """Proxies the request to create or update a configuration."""
    try:
        payload = await request.json()
        async with await get_backend_client() as client:
            response = await client.post("/core/config", json=payload)
            response.raise_for_status()
            await client.delete(f"/core/config/cache/{payload['key']}")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Backend error updating config", detail=e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
    except httpx.RequestError as e:
        logger.error("Network error updating config", error=str(e))
        raise HTTPException(status_code=502, detail="Bad Gateway: Cannot connect to backend service.")


app.mount("/", StaticFiles(directory="static", html=True), name="static")