"""HTTP route handlers for food-truck list and nearby-search operations."""

from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db.session import get_connection
from app.repositories.food_truck_repository import FoodTruck, FoodTruckRepository
from app.schemas.food_truck import FoodTruckOut, NearbyQueryParams
from app.services.food_truck_service import FoodTruckService, NearbyFoodTruck


router = APIRouter(prefix="/food-trucks", tags=["Food trucks"])


def get_food_truck_service() -> Generator[FoodTruckService, None, None]:
    """Create a request-scoped service with a request-scoped SQLite connection."""
    connection = get_connection()
    try:
        yield FoodTruckService(FoodTruckRepository(connection))
    finally:
        connection.close()


def _to_output(truck: FoodTruck, distance_km: float | None = None) -> FoodTruckOut:
    """Translate an internal domain record into the documented API response shape."""
    return FoodTruckOut(
        id=truck.id,
        name=truck.name,
        food_items=truck.food_items,
        lat=truck.latitude,
        lng=truck.longitude,
        address=truck.address,
        status=truck.status,
        schedule=truck.schedule,
        facility_type=truck.facility_type,
        distance_km=distance_km,
    )


@router.get("", response_model=list[FoodTruckOut], summary="List food trucks")
def list_food_trucks(
    service: Annotated[FoodTruckService, Depends(get_food_truck_service)],
    offset: Annotated[int, Query(ge=0, description="Number of records to skip.")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum records to return.")] = 100,
    food_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> list[FoodTruckOut]:
    """Return a paginated list of stored food-truck locations."""
    trucks = service.list_food_trucks(food_type=food_type)
    return [_to_output(truck) for truck in trucks[offset : offset + limit]]


@router.get("/nearby", response_model=list[FoodTruckOut], summary="Find nearby food trucks")
def find_nearby_food_trucks(
    query: Annotated[NearbyQueryParams, Depends()],
    service: Annotated[FoodTruckService, Depends(get_food_truck_service)],
) -> list[FoodTruckOut]:
    """Return nearby food trucks ordered from nearest to farthest."""
    nearby_trucks = service.find_nearby(
        latitude=query.lat,
        longitude=query.lng,
        radius_km=query.radius_km,
        food_type=query.food_type,
    )
    return [
        _to_output(result.truck, distance_km=result.distance_km)
        for result in nearby_trucks
    ]
