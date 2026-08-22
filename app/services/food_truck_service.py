"""Nearby-search business logic for food trucks."""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from app.repositories.food_truck_repository import FoodTruck, FoodTruckRepository


EARTH_RADIUS_KM = 6_371.0088


@dataclass(frozen=True)
class NearbyFoodTruck:
    """A food truck paired with its distance from a search location."""

    truck: FoodTruck
    distance_km: float


def haversine_distance_km(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    """Calculate the great-circle distance between two WGS84 points in kilometres.

    The Haversine formula projects latitude/longitude coordinates onto a sphere.
    It is accurate enough for nearby-map search and avoids the planar distortion
    that would result from subtracting degrees directly.
    """
    latitude_delta = radians(destination_latitude - origin_latitude)
    longitude_delta = radians(destination_longitude - origin_longitude)
    origin_latitude_radians = radians(origin_latitude)
    destination_latitude_radians = radians(destination_latitude)

    haversine_value = (
        sin(latitude_delta / 2) ** 2
        + cos(origin_latitude_radians)
        * cos(destination_latitude_radians)
        * sin(longitude_delta / 2) ** 2
    )
    angular_distance = 2 * asin(sqrt(haversine_value))
    return EARTH_RADIUS_KM * angular_distance


class FoodTruckService:
    """Coordinate nearby search while delegating persistence to the repository."""

    def __init__(self, repository: FoodTruckRepository) -> None:
        self._repository = repository

    def list_food_trucks(self, food_type: str | None = None) -> list[FoodTruck]:
        """Return all trucks, optionally narrowed by a food-description keyword."""
        normalized_food_type = food_type.strip() if food_type else None
        if normalized_food_type:
            return self._repository.get_by_food_type(normalized_food_type)
        return self._repository.get_all()

    def find_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float,
        food_type: str | None = None,
    ) -> list[NearbyFoodTruck]:
        """Find food trucks within a radius and sort results from nearest to farthest."""
        self._validate_search_coordinates(latitude, longitude, radius_km)

        candidates = self.list_food_trucks(food_type)
        nearby_trucks = [
            NearbyFoodTruck(
                truck=truck,
                distance_km=haversine_distance_km(
                    latitude,
                    longitude,
                    truck.latitude,
                    truck.longitude,
                ),
            )
            for truck in candidates
        ]

        return sorted(
            (result for result in nearby_trucks if result.distance_km <= radius_km),
            key=lambda result: (result.distance_km, result.truck.id),
        )

    @staticmethod
    def _validate_search_coordinates(latitude: float, longitude: float, radius_km: float) -> None:
        """Reject invalid map coordinates and a negative search radius."""
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("Latitude must be between -90 and 90.")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError("Longitude must be between -180 and 180.")
        if radius_km < 0:
            raise ValueError("radius_km must be greater than or equal to zero.")
