"""Unit tests for food-truck nearby-search business logic."""

import sqlite3

import pytest

from app.db.session import create_food_trucks_table
from app.repositories.food_truck_repository import FoodTruckRepository
from app.services.food_truck_service import FoodTruckService, haversine_distance_km


@pytest.fixture
def service() -> FoodTruckService:
    """Build a service backed by deterministic in-memory food-truck records."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_food_trucks_table(connection)
    connection.executemany(
        """
        INSERT INTO food_trucks (
            source_id, name, food_items, latitude, longitude, address, status, schedule, facility_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "one",
                "Origin Tacos",
                "Tacos; Burritos",
                37.7749,
                -122.4194,
                "1 Market St",
                "APPROVED",
                None,
                "Truck",
            ),
            (
                "two",
                "Nearby Coffee",
                "Coffee; Pastries",
                37.7759,
                -122.4194,
                "2 Market St",
                "APPROVED",
                None,
                "Truck",
            ),
            (
                "three",
                "Distant Tacos",
                "Tacos",
                37.8044,
                -122.2712,
                "3 Market St",
                "APPROVED",
                None,
                "Truck",
            ),
        ],
    )
    connection.commit()

    try:
        yield FoodTruckService(FoodTruckRepository(connection))
    finally:
        connection.close()


def test_haversine_distance_matches_known_one_degree_equatorial_distance() -> None:
    """One degree of longitude at the equator is approximately 111.195 km."""
    assert haversine_distance_km(0, 0, 0, 1) == pytest.approx(111.195, abs=0.01)


def test_nearby_search_filters_by_radius_and_sorts_nearest_first(
    service: FoodTruckService,
) -> None:
    """Nearby search excludes distant locations and sorts the retained locations."""
    results = service.find_nearby(
        latitude=37.7749,
        longitude=-122.4194,
        radius_km=0.2,
    )

    assert [result.truck.name for result in results] == ["Origin Tacos", "Nearby Coffee"]
    assert results[0].distance_km == pytest.approx(0)
    assert results[0].distance_km < results[1].distance_km


def test_nearby_search_filters_food_items_case_insensitively(service: FoodTruckService) -> None:
    """Food-type search delegates keyword selection without including other cuisines."""
    results = service.find_nearby(
        latitude=37.7749,
        longitude=-122.4194,
        radius_km=20,
        food_type="TACO",
    )

    assert [result.truck.name for result in results] == ["Origin Tacos", "Distant Tacos"]
