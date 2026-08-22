"""Pydantic models used by the food-truck HTTP API."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings


def default_radius_km() -> float:
    """Resolve the configured default radius when a request omits it."""
    return get_settings().default_radius_km


class NearbyQueryParams(BaseModel):
    """Validated query parameters for a nearby food-truck search."""

    model_config = ConfigDict(validate_default=True)

    lat: float = Field(description="Search latitude in WGS84 degrees.", ge=-90, le=90)
    lng: float = Field(description="Search longitude in WGS84 degrees.", ge=-180, le=180)
    radius_km: float = Field(
        default_factory=default_radius_km,
        description="Maximum search radius in kilometres.",
        ge=0,
    )
    food_type: str | None = Field(
        default=None,
        description="Optional case-insensitive keyword matched against food items.",
        min_length=1,
        max_length=100,
    )


class FoodTruckOut(BaseModel):
    """A food-truck record returned from the public API."""

    id: int
    name: str
    food_items: str | None
    lat: float
    lng: float
    address: str | None
    status: str | None
    schedule: str | None
    facility_type: str | None
    distance_km: float | None = Field(
        default=None,
        description="Distance from the nearby-search origin, when applicable.",
    )
