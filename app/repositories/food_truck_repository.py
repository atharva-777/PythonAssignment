"""SQLite persistence access for food-truck records."""

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class FoodTruck:
    """A food-truck record returned from the local SQLite dataset."""

    id: int
    source_id: str
    name: str
    food_items: str | None
    latitude: float
    longitude: float
    address: str | None
    status: str | None
    schedule: str | None
    facility_type: str | None


class FoodTruckRepository:
    """Perform database-only queries for food-truck records."""

    _SELECT_COLUMNS = """
        id,
        source_id,
        name,
        food_items,
        latitude,
        longitude,
        address,
        status,
        schedule,
        facility_type
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_all(self) -> list[FoodTruck]:
        """Return every stored food truck in a stable database order."""
        return self._fetch_many(
            f"SELECT {self._SELECT_COLUMNS} FROM food_trucks ORDER BY id",
            (),
        )

    def get_by_food_type(self, food_type: str) -> list[FoodTruck]:
        """Return trucks whose food description contains the supplied keyword."""
        return self._fetch_many(
            f"""
            SELECT {self._SELECT_COLUMNS}
            FROM food_trucks
            WHERE food_items LIKE ? COLLATE NOCASE
            ORDER BY id
            """,
            (f"%{food_type}%",),
        )

    def _fetch_many(self, query: str, parameters: tuple[object, ...]) -> list[FoodTruck]:
        """Execute one query and map its rows without applying business rules."""
        rows = self._connection.execute(query, parameters).fetchall()
        return [self._to_food_truck(row) for row in rows]

    @staticmethod
    def _to_food_truck(row: sqlite3.Row) -> FoodTruck:
        """Map a SQLite row to the repository's domain record."""
        return FoodTruck(
            id=row["id"],
            source_id=row["source_id"],
            name=row["name"],
            food_items=row["food_items"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            address=row["address"],
            status=row["status"],
            schedule=row["schedule"],
            facility_type=row["facility_type"],
        )
