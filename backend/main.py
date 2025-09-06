from contextlib import asynccontextmanager

import structlog
import structlog.contextvars
from config import settings
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from plugins import init_plugins
from prometheus_fastapi_instrumentator import Instrumentator
from pymongo.errors import ConnectionFailure
from utils.database_setup import ensure_indexes
from utils.exceptions import ServiceError
from utils.fal_client import FalAIClient
from utils.llm_client import LLMClient
from utils.middleware import api_key_middleware, structured_logging_middleware
from utils.redis_client import close_redis_client, init_redis_client

from kurisu_core.logging_config import setup_structlog
from kurisu_core.tracing import setup_tracing

EXCLUDED_PLUGINS = []

setup_structlog(json_logs=settings.json_logs)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application's lifespan.
    Connects to all required services on startup and gracefully disconnects on shutdown.
    """
    setup_tracing(service_name=settings.service_name)
    HTTPXClientInstrumentor().instrument()
    logger.info("Application starting up...", service=settings.service_name)

    instrumentator.expose(app)
    logger.info("Prometheus metrics endpoint exposed at /metrics.")

    try:
        app.state.mongo_client = AsyncIOMotorClient(str(settings.mongodb_url))
        await app.state.mongo_client.admin.command("ping")
        logger.info("Successfully connected to MongoDB.")

        db = app.state.mongo_client[settings.mongodb_database]
        await ensure_indexes(db)
    except ConnectionFailure as e:
        logger.fatal("Failed to connect to MongoDB on startup.", error=str(e))
        raise

    app.state.redis = await init_redis_client()
    logger.info("Successfully connected to Redis.")

    app.state.llm_client = LLMClient(
        api_key=settings.llm_api_key,
        base_url=str(settings.llm_base_url),
        http_referer=settings.llm_http_referer,
        x_title=settings.llm_x_title,
    )
    logger.info("LLM Client initialized.")

    app.state.fal_client = FalAIClient(api_key=settings.fal_api_key)
    logger.info("Fal.ai Client initialized.")

    yield

    logger.info("Application shutting down...")
    app.state.mongo_client.close()
    logger.info("MongoDB connection closed.")

    await close_redis_client()
    logger.info("Redis connection closed.")


app = FastAPI(
    version="1.0.0",
    title="Kurisu API",
    description="Dynamic plugin-based API with autodiscovery, metrics, and structured logging.",
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health"],
)

instrumentator.instrument(app, metric_namespace="kurisu", metric_subsystem="backend")


@app.exception_handler(ServiceError)
async def service_exception_handler(request: Request, exc: ServiceError):
    logger.warning(
        "Service error occurred, returning HTTP response",
        detail=exc.detail,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "An unhandled exception occurred",
        error=str(exc),
    )
    context_vars = structlog.contextvars.get_contextvars()
    correlation_id = context_vars.get("correlation_id", "not-available")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "error_id": correlation_id,
        },
    )


app.middleware("http")(api_key_middleware)
app.middleware("http")(structured_logging_middleware)

init_plugins(app, excluded_plugins=EXCLUDED_PLUGINS)


@app.get("/health", tags=["Health Check"], include_in_schema=False)
def health_check():
    return {"status": "ok"}
