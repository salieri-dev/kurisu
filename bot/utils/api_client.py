"""Backend API client for bot plugins."""

import uuid
from typing import Any

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
            timeout=30.0,
        )

    async def _prepare_headers(
        self, message: Message, correlation_id: str | None = None
    ) -> dict[str, str]:
        """Prepare headers for API request from a Pyrogram message object."""
        if message.chat is None:
            raise ValueError("Message must have a valid chat")
        user = message.from_user
        if user is None:
            raise ValueError("Message must have a valid user")

        headers = {
            "X-Correlation-ID": correlation_id or str(uuid.uuid4()),
            "X-Chat-ID": str(message.chat.id),
            "X-User-ID": str(user.id),
            "X-User-Name": user.username
            or f"{user.first_name or ''} {user.last_name or ''}".strip()
            or "Unknown",
        }

        propagate.inject(headers)

        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        message: Message,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a generic HTTP request to the backend API.
        """
        correlation_id = str(uuid.uuid4())

        with tracer.start_as_current_span(
            f"call_backend:{method}",
            attributes={
                "http.method": method,
                "http.url": f"{self._client.base_url}{path}",
            },
        ) as span:
            try:
                headers = await self._prepare_headers(message, correlation_id)
                span.set_attribute("correlation_id", correlation_id)

                response = await self._client.request(
                    method, path, params=params, json=json, headers=headers
                )

                span.set_attribute("http.status_code", response.status_code)
                response.raise_for_status()

                response_correlation_id = response.headers.get(
                    "X-Correlation-ID", correlation_id
                )
                log.info(
                    "Backend request successful",
                    method=method,
                    path=path,
                    correlation_id=response_correlation_id,
                    status_code=response.status_code,
                )
                return response.json()

            except httpx.HTTPStatusError as e:
                span.set_attribute("http.status_code", e.response.status_code)
                span.set_attribute("error", True)
                span.record_exception(e)

                response_correlation_id = e.response.headers.get(
                    "X-Correlation-ID", correlation_id
                )
                try:
                    error_data = e.response.json()
                    detail = error_data.get("detail", "No detail provided by API.")
                except Exception:
                    detail = (
                        f"Failed to parse error response. Body: {e.response.text[:200]}"
                    )

                log.warning(
                    "Backend API returned an error status",
                    method=method,
                    path=path,
                    correlation_id=response_correlation_id,
                    status_code=e.response.status_code,
                    detail=detail,
                )
                raise APIError(
                    detail=detail,
                    status_code=e.response.status_code,
                    correlation_id=response_correlation_id,
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
        self, path: str, *, message: Message, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request to the backend API."""
        return await self.request("GET", path, message=message, params=params)

    async def post(
        self, path: str, *, message: Message, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a POST request to the backend API."""
        return await self.request("POST", path, message=message, json=json)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


backend_client = BackendClient(credentials.backend_url, credentials.api_key)
