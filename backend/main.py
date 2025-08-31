from contextlib import asynccontextmanager

import structlog
from config import settings
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from plugins import init_plugins
from pymongo.errors import ConnectionFailure
from utils.exceptions import ServiceError
from utils.middleware import api_key_middleware, structured_logging_middleware

from kurisu_core.logging_config import setup_structlog

EXCLUDED_PLUGINS = []

setup_structlog(json_logs=settings.json_logs)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application's lifespan. Connect to DB on startup, disconnect on shutdown.
    """
    logger.info("Application starting up...", service=settings.service_name)
    try:
        app.state.mongo_client = AsyncIOMotorClient(str(settings.mongodb_url))
        await app.state.mongo_client.admin.command("ping")
        logger.info("Successfully connected to MongoDB.")
    except ConnectionFailure as e:
        logger.fatal("Failed to connect to MongoDB on startup.", error=str(e))

        raise

    yield

    logger.info("Application shutting down...")
    app.state.mongo_client.close()
    logger.info("MongoDB connection closed.")


app = FastAPI(
    version="1.0.0",
    title="Kurisu API",
    description="Dynamic plugin-based API with autodiscovery",
    lifespan=lifespan,
)


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


app.middleware("http")(structured_logging_middleware)
app.middleware("http")(api_key_middleware)

init_plugins(app, excluded_plugins=EXCLUDED_PLUGINS)


@app.get("/health", tags=["Health Check"])
def read_root(request: Request):
    logger.info("Health check endpoint hit")
    return {"status": "ok"}
