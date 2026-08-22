"""Integration tests for the food-truck HTTP API."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes.food_trucks import get_food_truck_service
from app.db.session import create_food_trucks_table, get_connection
from app.main import app
from app.repositories.food_truck_repository import FoodTruckRepository
from app.services.food_truck_service import FoodTruckService


def _seed_test_database(database_url: str) -> None:
    """Create a deterministic SQLite dataset used only by API integration tests."""
    connection = get_connection(database_url)
    try:
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
                    "Far Tacos",
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
    finally:
        connection.close()


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    """Return a TestClient whose route dependency uses an isolated SQLite database."""
    database_url = f"sqlite:///{(tmp_path / 'food_trucks.db').as_posix()}"
    _seed_test_database(database_url)

    def get_test_service() -> Generator[FoodTruckService, None, None]:
        connection = get_connection(database_url)
        try:
            yield FoodTruckService(FoodTruckRepository(connection))
        finally:
            connection.close()

    app.dependency_overrides[get_food_truck_service] = get_test_service
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_nearby_endpoint_returns_sorted_distance_annotated_results(client: TestClient) -> None:
    """Nearby endpoint returns only radius matches in increasing distance order."""
    response = client.get(
        "/api/v1/food-trucks/nearby",
        params={"lat": 37.7749, "lng": -122.4194, "radius_km": 0.2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [truck["name"] for truck in payload] == ["Origin Tacos", "Nearby Coffee"]
    assert payload[0]["distance_km"] == pytest.approx(0)
    assert payload[0]["distance_km"] < payload[1]["distance_km"]
    assert {"id", "name", "food_items", "lat", "lng", "address", "distance_km"} <= payload[0].keys()


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 91, "lng": -122.4194},
        {"lat": 37.7749, "lng": -181},
        {"lat": 37.7749, "lng": -122.4194, "radius_km": -1},
    ],
)
def test_nearby_endpoint_rejects_invalid_coordinates_or_radius(
    client: TestClient,
    params: dict[str, float],
) -> None:
    """Invalid nearby-search inputs produce FastAPI's clear validation response."""
    response = client.get("/api/v1/food-trucks/nearby", params=params)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_list_endpoint_paginates_and_leaves_distance_empty(client: TestClient) -> None:
    """List endpoint supports pagination and does not invent a distance origin."""
    response = client.get("/api/v1/food-trucks", params={"offset": 1, "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert [truck["name"] for truck in payload] == ["Nearby Coffee"]
    assert payload[0]["distance_km"] is None
