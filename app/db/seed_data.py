"""Fetch DataSF food-truck records and load them into SQLite."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import sqlite3
from typing import Any

import requests

from app.core.config import Settings, get_settings
from app.db.session import create_food_trucks_table, get_connection


logger = logging.getLogger(__name__)


class DataIngestionError(RuntimeError):
    """Raised when the remote food-truck dataset cannot be retrieved or decoded."""


@dataclass(frozen=True)
class SeedResult:
    """Summary returned after a data-seeding run."""

    fetched: int
    loaded: int
    skipped: int


def _clean_text(value: Any) -> str | None:
    """Return a stripped string or ``None`` for empty source values."""
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _parse_coordinate(value: Any, field_name: str, row_identifier: str) -> float | None:
    """Parse and validate a WGS84 coordinate, logging invalid values for review."""
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        logger.warning(
            "Skipping food-truck record with missing or invalid coordinate",
            extra={"row_id": row_identifier, "field": field_name, "value": value},
        )
        return None

    valid_range = (-90.0, 90.0) if field_name == "latitude" else (-180.0, 180.0)
    if not math.isfinite(coordinate) or not valid_range[0] <= coordinate <= valid_range[1]:
        logger.warning(
            "Skipping food-truck record with out-of-range coordinate",
            extra={"row_id": row_identifier, "field": field_name, "value": value},
        )
        return None

    return coordinate


def _record_from_source(
    row: dict[str, Any],
) -> tuple[str, str, str | None, float, float, str | None, str | None, str | None, str | None] | None:
    """Convert a SODA row to a database record, skipping malformed coordinates."""
    name = _clean_text(row.get("applicant")) or "Unknown vendor"
    address = _clean_text(row.get("address"))
    source_id = _clean_text(row.get("locationid")) or _clean_text(row.get("objectid"))
    row_identifier = source_id or address or name

    latitude = _parse_coordinate(row.get("latitude"), "latitude", row_identifier)
    longitude = _parse_coordinate(row.get("longitude"), "longitude", row_identifier)
    if latitude is None or longitude is None:
        return None

    # Older or derived DataSF views can omit locationid. This stable fallback keeps
    # repeated seed runs idempotent without discarding an otherwise valid row.
    if source_id is None:
        source_id = f"{name}|{address or ''}|{latitude:.7f}|{longitude:.7f}"

    return (
        source_id,
        name,
        _clean_text(row.get("fooditems")),
        latitude,
        longitude,
        address,
        _clean_text(row.get("status")),
        _clean_text(row.get("schedule")),
        _clean_text(row.get("facilitytype")),
    )


def fetch_food_truck_rows(url: str, timeout_seconds: float) -> list[dict[str, Any]]:
    """Fetch and validate the list payload returned by the configured SODA endpoint."""
    try:
        response = requests.get(url, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as error:
        raise DataIngestionError(f"Unable to fetch food-truck data from {url}") from error

    try:
        payload = response.json()
    except ValueError as error:
        raise DataIngestionError("DataSF returned a non-JSON food-truck response") from error

    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise DataIngestionError("DataSF response must be a JSON list of objects")

    return payload


def seed_food_trucks(settings: Settings | None = None) -> SeedResult:
    """Download DataSF food trucks and atomically replace the local search dataset."""
    active_settings = settings or get_settings()
    source_rows = fetch_food_truck_rows(
        active_settings.food_truck_data_url,
        active_settings.food_truck_request_timeout_seconds,
    )

    records = [record for row in source_rows if (record := _record_from_source(row)) is not None]
    skipped = len(source_rows) - len(records)

    connection: sqlite3.Connection = get_connection(active_settings.database_url)
    try:
        create_food_trucks_table(connection)
        with connection:
            connection.execute("DELETE FROM food_trucks")
            connection.executemany(
                """
                INSERT INTO food_trucks (
                    source_id, name, food_items, latitude, longitude, address, status, schedule, facility_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
    finally:
        connection.close()

    result = SeedResult(fetched=len(source_rows), loaded=len(records), skipped=skipped)
    logger.info(
        "Food-truck data seeding completed",
        extra={"fetched": result.fetched, "loaded": result.loaded, "skipped": result.skipped},
    )
    return result


def main() -> None:
    """Run the ingestion command with settings resolved from the environment."""
    try:
        result = seed_food_trucks()
    except DataIngestionError:
        logger.exception("Food-truck data seeding failed")
        raise SystemExit(1) from None

    print(f"Seeded {result.loaded} food-truck records; skipped {result.skipped} malformed rows.")


if __name__ == "__main__":
    main()
