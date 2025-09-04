# backend/plugins/utilities/debug/endpoint.py
import asyncio
import time

import structlog
from fastapi import APIRouter, HTTPException
from opentelemetry import trace

from .models import DebugRequest

router = APIRouter()
logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


@router.post(
    "/generate",
    summary="Generate a Test Event",
    description="Triggers various test events like logs, errors, and traces based on the request body.",
)
async def generate_test_event(request: DebugRequest):
    """
    This endpoint is a sandbox for testing the observability stack.
    """
    # 1. Generate a custom trace with child spans if requested
    if request.create_spans:
        with tracer.start_as_current_span("complex_operation") as parent_span:
            parent_span.set_attribute("debug.mode", True)
            time.sleep(0.05)  # Simulate initial work

            with tracer.start_as_current_span("simulated_db_call") as child_span_1:
                child_span_1.add_event("Connecting to database...")
                await asyncio.sleep(0.1)
                child_span_1.add_event("Query successful.")

            with tracer.start_as_current_span("data_processing") as child_span_2:
                await asyncio.sleep(0.15)
                child_span_2.set_attribute("items.processed", 100)

            parent_span.add_event("Complex operation finished.")

    # 2. Add an artificial delay if requested
    if request.delay_seconds > 0:
        await asyncio.sleep(request.delay_seconds)

    # 3. Generate the log message at the specified level
    log_payload = {"test_parameter": "some_value", "user_request": request.model_dump()}
    if request.log_level == "info":
        logger.info(request.log_message, **log_payload)
    elif request.log_level == "warning":
        logger.warning(request.log_message, **log_payload)
    elif request.log_level == "error":
        logger.error(request.log_message, **log_payload)
    elif request.log_level == "exception":
        try:
            _ = 1 / 0
        except ZeroDivisionError:
            logger.exception(request.log_message, **log_payload)

    # 4. Return the appropriate HTTP status code
    if request.http_status_code != 200:
        raise HTTPException(
            status_code=request.http_status_code,
            detail=f"This is a simulated HTTP error with status code {request.http_status_code}.",
        )

    return {
        "status": "success",
        "message": "Debug event generated successfully.",
        "details": request.model_dump(),
    }
