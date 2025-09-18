import time
import uuid
import structlog
import structlog.contextvars
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

EXCLUDED_ENDPOINTS = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/metrics",
]


async def structured_logging_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    start_time = time.time()
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        user_id=request.headers.get("x-user-id"),
        chat_id=request.headers.get("x-chat-id"),
        user_name=request.headers.get("x-user-name"),
        remote_addr=request.client.host if request.client else None,
        request_path=request.url.path,
        request_method=request.method,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code
        log_event = logger.info if 200 <= status_code < 400 else logger.warning
        log_details = {
            "status_code": status_code,
            "processing_time_ms": round(process_time * 1000, 2),
        }
        if status_code == 401:
            log_details["auth_error"] = "Invalid or missing API key"
        log_event("Request completed", **log_details)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response
    except Exception:
        process_time = time.time() - start_time
        logger.exception(
            "Request failed with unhandled exception",
            processing_time_ms=round(process_time * 1000, 2),
        )
        raise
    finally:
        structlog.contextvars.clear_contextvars()


async def api_key_middleware(request: Request, call_next, settings):
    """
    Middleware to verify API key.
    """
    if request.url.path in EXCLUDED_ENDPOINTS:
        return await call_next(request)

    api_key = request.headers.get("x-api-key")
    expected_api_key = settings.api_key

    if not api_key or api_key != expected_api_key:
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or missing API key"}
        )
    return await call_next(request)
