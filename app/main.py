"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.food_trucks import router as food_trucks_router
from app.db.session import create_food_trucks_table, get_connection


@asynccontextmanager
async def lifespan(_: FastAPI) -> Generator[None, None, None]:
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
