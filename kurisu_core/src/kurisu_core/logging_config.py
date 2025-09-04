import logging
import logging.config
import os
import sys

import structlog
from opentelemetry import trace
from structlog.types import EventDict, Processor


def add_opentelemetry_ids(_, __, event_dict: EventDict) -> EventDict:
    """
    Adds trace_id and span_id to the log record if a trace is active.
    """
    current_span = trace.get_current_span()
    if current_span.get_span_context().is_valid:
        event_dict["trace_id"] = trace.format_trace_id(
            current_span.get_span_context().trace_id
        )
        event_dict["span_id"] = trace.format_span_id(
            current_span.get_span_context().span_id
        )
    return event_dict


def add_service_info(_, __, event_dict: EventDict) -> EventDict:
    event_dict["service"] = os.getenv("SERVICE_NAME", "unknown")
    event_dict["env"] = os.getenv("ENVIRONMENT", "development")
    return event_dict


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def setup_structlog(json_logs: bool = False, log_level: str = "INFO"):
    """
    Configure structured logging for the entire application.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_service_info,
        add_opentelemetry_ids,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "structlog.stdlib.ProcessorFormatter",
                    "processors": [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer()
                        if json_logs
                        else structlog.dev.ConsoleRenderer(colors=True),
                    ],
                    "foreign_pre_chain": shared_processors,
                },
            },
            "handlers": {
                "default": {
                    "level": log_level.upper(),
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": log_level.upper(),
                    "propagate": True,
                },
                "uvicorn": {
                    "handlers": [],
                    "level": log_level.upper(),
                    "propagate": True,
                },
                "uvicorn.error": {
                    "handlers": [],
                    "level": log_level.upper(),
                    "propagate": True,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "propagate": False,
                },
            },
        }
    )

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        structlog.get_logger("uncaught_exception").error(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception
