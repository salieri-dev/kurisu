"""Backend API client for bot plugins."""

import uuid
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

import httpx
import structlog
from config import credentials
from opentelemetry import propagate, trace
from pyrogram.types import Message
from utils.exceptions import APIError

log = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class BackendClient:
    """Generic backend API client for all bot plugins."""

    def __init__(self, base_url: str, api_key: str | None = None):
        """Initialize the backend client."""
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key} if api_key else {},
            timeout=180.0,
        )

    async def _prepare_headers(
        self, message: Optional[Message], correlation_id: str
    ) -> dict[str, str]:
        """
        Prepare headers for API request.
        Derives context from a Pyrogram message if provided, otherwise uses system context.
        """
        headers = {"X-Correlation-ID": correlation_id}

        if message and message.chat and message.from_user:
            user = message.from_user
            headers.update(
                {
                    "X-Chat-ID": str(message.chat.id),
                    "X-User-ID": str(user.id),
                    "X-User-Name": user.username
                    or f"{user.first_name or ''} {user.last_name or ''}".strip()
                    or "Unknown",
                }
            )
        else:
            headers.update(
                {
                    "X-Chat-ID": "system",
                    "X-User-ID": "system",
                    "X-User-Name": "KurisuBotSystem",
                }
            )

        propagate.inject(headers)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        message: Optional[Message] = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Make a generic HTTP request to the backend API.
        Handles both user-initiated and system-level requests.
        """
        correlation_id = str(uuid.uuid4())

        with tracer.start_as_current_span(
            f"call_backend:{method}",
            attributes={
                "http.method": method,
                "http.url": f"{self._client.base_url}{path}",
                "request.type": "user" if message else "system",
            },
        ) as span:
            try:
                headers = await self._prepare_headers(message, correlation_id)
                span.set_attribute("correlation_id", correlation_id)

                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                    headers=headers,
                )

                span.set_attribute("http.status_code", response.status_code)
                response.raise_for_status()

                log.info(
                    "Backend request successful",
                    method=method,
                    path=path,
                    correlation_id=correlation_id,
                    status_code=response.status_code,
                )
                return response

            except httpx.HTTPStatusError as e:
                span.set_attribute("http.status_code", e.response.status_code)
                span.set_attribute("error", True)
                span.record_exception(e)
                try:
                    detail = e.response.json().get("detail", "API Error")
                except Exception:
                    detail = e.response.text or "API Error"

                log.warning(
                    "Backend API returned an error status",
                    method=method,
                    path=path,
                    correlation_id=correlation_id,
                    status_code=e.response.status_code,
                    detail=detail,
                )
                raise APIError(
                    detail=detail,
                    status_code=e.response.status_code,
                    correlation_id=correlation_id,
                ) from e

            except httpx.RequestError as e:
                span.set_attribute("error", True)
                span.record_exception(e)
                log.error(
                    "Backend API request network error",
                    method=method,
                    path=path,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise APIError(
                    detail=f"Network error communicating with the backend: {e.__class__.__name__}",
                    status_code=503,
                    correlation_id=correlation_id,
                ) from e

    async def get(
        self,
        path: str,
        *,
        message: Optional[Message] = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GET request to the backend API."""
        response = await self.request("GET", path, message=message, params=params)
        return response.json()

    async def post(
        self,
        path: str,
        *,
        message: Optional[Message] = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to the backend API."""
        response = await self.request("POST", path, message=message, json=json)
        return response.json()

    async def post_media(
        self,
        path: str,
        *,
        message: Optional[Message] = None,
        file_bytes: BytesIO,
        file_name: str,
        file_mime: str,
        data: Optional[Dict[str, Any]] = None,
        file_part_name: str = "file",
    ) -> Tuple[bytes, str]:
        """Make a POST request with a file and return the content and content-type."""
        files = {file_part_name: (file_name, file_bytes, file_mime)}
        response = await self.request(
            "POST", path, message=message, data=data, files=files
        )
        content_type = response.headers.get("content-type", "application/octet-stream")
        return response.content, content_type

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


backend_client = BackendClient(credentials.backend_url, credentials.api_key)
