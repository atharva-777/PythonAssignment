"""FastAPI application entry point."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.routes.food_trucks import router as food_trucks_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.session import create_food_trucks_table, get_connection


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Ensure a fresh installation can serve an empty dataset before seeding."""
    connection = get_connection()
    try:
        create_food_trucks_table(connection)
        connection.commit()
    finally:
        connection.close()

    yield


app = FastAPI(
    title="Food Trucks Nearby Search API",
    version="0.1.0",
    description="Find San Francisco food trucks near a map location.",
    lifespan=lifespan,
)
app.include_router(food_trucks_router, prefix="/api/v1")


@app.middleware("http")
async def log_request_outcome(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log each request's method, query parameters, response status, and duration."""
    started_at = perf_counter()
    request_details = {
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
    }

    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            "Request failed unexpectedly",
            extra={
                **request_details,
                "status_code": 500,
                "error_type": type(error).__name__,
            },
        )
        raise

    logger.info(
        "Request completed",
        extra={
            **request_details,
            "status_code": response.status_code,
            "duration_ms": round((perf_counter() - started_at) * 1_000, 2),
        },
    )
    return response


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
    """Return a safe response for unhandled errors while retaining traceback logs."""
    logger.exception(
        "Unhandled application error",
        extra={"method": request.method, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )
