"""SQLite connection and schema helpers."""

from pathlib import Path
import sqlite3

from app.core.config import get_settings


CREATE_FOOD_TRUCKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS food_trucks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    food_items TEXT,
    latitude REAL NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude REAL NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    address TEXT,
    status TEXT,
    schedule TEXT,
    facility_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_food_trucks_coordinates
    ON food_trucks (latitude, longitude);
"""


def database_path_from_url(database_url: str) -> str:
    """Translate a supported SQLite URL into the path accepted by ``sqlite3``."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("DATABASE_URL must use the sqlite:/// URL format.")

    database_path = database_url.removeprefix(prefix)
    if database_path == ":memory:":
        return database_path

    return str(Path(database_path))


def get_connection(database_url: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection configured to return mapping-style rows."""
    configured_url = database_url or get_settings().database_url
    database_path = database_path_from_url(configured_url)

    if database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_food_trucks_table(connection: sqlite3.Connection) -> None:
    """Create the food-truck table and its location index when absent."""
    connection.executescript(CREATE_FOOD_TRUCKS_TABLE_SQL)
