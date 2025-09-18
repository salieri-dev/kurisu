from typing import Annotated, Any, Dict
from fastapi import APIRouter, Depends, BackgroundTasks
import structlog
from .service import MessageService, get_message_service

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/save", status_code=202)
async def save_message(
    message_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    service: Annotated[MessageService, Depends(get_message_service)],
):
    """
    Accepts a message from the bot, saves it, and queues it for further
    processing in the background. Returns immediately with 202 Accepted.
    """
    correlation_id = message_data.get("correlation_id")
    chat_id = message_data.get("chat", {}).get("id")
    message_id = message_data.get("id")

    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        chat_id=chat_id,
        message_id=message_id,
    )

    logger.info("Received message to save")

    background_tasks.add_task(service.save_and_process_message, message_data)

    return {"status": "accepted"}
