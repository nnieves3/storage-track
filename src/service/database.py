from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, LiteralString

from .models import InventoryItem, Location, SubLocation
from .repository import InventoryRepository


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS inventory_locations (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS inventory_sub_locations (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(location_id, name)
);

CREATE TABLE IF NOT EXISTS inventory_items (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    count INTEGER NOT NULL DEFAULT 1 CHECK (count >= 0),
    location_id BIGINT REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    sub_location_id BIGINT REFERENCES inventory_sub_locations(id) ON DELETE RESTRICT,
    checked_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS inventory_items_name_idx ON inventory_items (name);
ALTER TABLE inventory_items
    ADD COLUMN IF NOT EXISTS location_id BIGINT;
ALTER TABLE inventory_items
    ADD COLUMN IF NOT EXISTS sub_location_id BIGINT;
ALTER TABLE inventory_items
    ADD COLUMN IF NOT EXISTS checked_out BOOLEAN NOT NULL DEFAULT FALSE;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'inventory_items'
          AND column_name = 'checked_out_count'
    ) THEN
        UPDATE inventory_items
        SET checked_out = checked_out_count > 0;
        ALTER TABLE inventory_items DROP COLUMN checked_out_count;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS inventory_items_location_idx
    ON inventory_items (location_id, sub_location_id);
"""


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "storage_track"
    user: str = "postgres"
    password: str | None = None

    @property
    def dsn(self) -> str:
        password = "" if self.password is None else self.password
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={password}"
        )


class PostgresInventoryRepository(InventoryRepository):
    def __init__(
        self,
        config: DatabaseConfig,
        connection_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        if connection_factory is None:
            try:
                import psycopg
            except ImportError as exc:
                raise RuntimeError(
                    "PostgreSQL support requires the 'psycopg[binary]' package"
                ) from exc
            self._connect = psycopg.connect
        else:
            self._connect = connection_factory

    def initialize(self) -> None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(SCHEMA_SQL)

    def create_location(self, name: str) -> Location:
        Location(name)
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO inventory_locations (name) VALUES (%s)
                    RETURNING id, name
                    """,
                    (name,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("failed to create inventory location")
                location_id, location_name = row
                cursor.execute(
                    """
                    INSERT INTO inventory_sub_locations
                        (location_id, name, is_default)
                    VALUES (%s, 'Other', TRUE)
                    RETURNING id, location_id, name
                    """,
                    (location_id,),
                )
                sub_row = cursor.fetchone()
                if sub_row is None:
                    raise RuntimeError("failed to create default sub-location")
                return Location(
                    id=location_id,
                    name=location_name,
                    sub_locations=[
                        SubLocation(id=sub_row[0], location_id=sub_row[1], name=sub_row[2])
                    ],
                )

    def get_location(self, location_id: int) -> Location | None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM inventory_locations WHERE id = %s",
                    (location_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute(
                    """
                    SELECT id, location_id, name
                    FROM inventory_sub_locations
                    WHERE location_id = %s
                    ORDER BY is_default DESC, name, id
                    """,
                    (location_id,),
                )
                sub_locations = [
                    SubLocation(id=item[0], location_id=item[1], name=item[2])
                    for item in cursor.fetchall()
                ]
                return Location(id=row[0], name=row[1], sub_locations=sub_locations)

    def list_locations(self) -> list[Location]:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM inventory_locations ORDER BY name, id")
                return [
                    location
                    for row in cursor.fetchall()
                    if (location := self.get_location(row[0])) is not None
                ]

    def remove_location(self, location_id: int) -> bool:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM inventory_items WHERE location_id = %s",
                    (location_id,),
                )
                item_count = cursor.fetchone()
                if item_count is None or item_count[0] > 0:
                    raise ValueError("location cannot be removed while items are assigned to it")
                cursor.execute(
                    "DELETE FROM inventory_sub_locations WHERE location_id = %s",
                    (location_id,),
                )
                cursor.execute(
                    "DELETE FROM inventory_locations WHERE id = %s",
                    (location_id,),
                )
                return cursor.rowcount > 0

    def create_sub_location(
        self, location_id: int, name: str
    ) -> SubLocation | None:
        SubLocation(name=name, location_id=location_id)
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM inventory_locations WHERE id = %s",
                    (location_id,),
                )
                if cursor.fetchone() is None:
                    return None
                cursor.execute(
                    """
                    INSERT INTO inventory_sub_locations (location_id, name)
                    VALUES (%s, %s)
                    RETURNING id, location_id, name
                    """,
                    (location_id, name),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return SubLocation(id=row[0], location_id=row[1], name=row[2])

    def get_sub_location(self, sub_location_id: int) -> SubLocation | None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, location_id, name FROM inventory_sub_locations WHERE id = %s",
                    (sub_location_id,),
                )
                row = cursor.fetchone()
                return None if row is None else SubLocation(
                    id=row[0], location_id=row[1], name=row[2]
                )

    def remove_sub_location(self, location_id: int, sub_location_id: int) -> bool:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT is_default FROM inventory_sub_locations
                    WHERE id = %s AND location_id = %s
                    """,
                    (sub_location_id, location_id),
                )
                row = cursor.fetchone()
                if row is None:
                    return False
                if row[0]:
                    raise ValueError("the Other sub-location cannot be removed")
                cursor.execute(
                    "SELECT 1 FROM inventory_items WHERE sub_location_id = %s LIMIT 1",
                    (sub_location_id,),
                )
                if cursor.fetchone() is not None:
                    raise ValueError(
                        "sub-location cannot be removed while items are assigned to it"
                    )
                cursor.execute(
                    "DELETE FROM inventory_sub_locations WHERE id = %s",
                    (sub_location_id,),
                )
                return cursor.rowcount > 0

    def add(self, item: InventoryItem) -> InventoryItem:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO inventory_items (name, description, count)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (item.name, item.description, item.count),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("failed to insert inventory item")
                item.id = row[0]
                return item

    def get(self, item_id: int) -> InventoryItem | None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(self._select_sql() + " WHERE i.id = %s", (item_id,))
                row = cursor.fetchone()
                return None if row is None else self._row_to_item(row)

    def list(self) -> list[InventoryItem]:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(self._select_sql() + " ORDER BY i.name, i.id")
                return [self._row_to_item(row) for row in cursor.fetchall()]

    def update(self, item: InventoryItem) -> InventoryItem | None:
        if item.id is None:
            raise ValueError("item.id is required for update")
        location_id = item.location.id if item.location else None
        sub_location_id = item.sub_location.id if item.sub_location else None
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE inventory_items
                    SET name = %s, description = %s, count = %s,
                        location_id = %s, sub_location_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        item.name, item.description, item.count,
                        location_id, sub_location_id, item.id,
                    ),
                )
                if cursor.rowcount == 0:
                    return None
        return self.get(item.id)

    def get_by_name(self, name: str) -> InventoryItem | None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute( self._select_sql() + " WHERE i.name = %s ORDER BY i.id LIMIT 1", (name,),)
                row = cursor.fetchone()
                return None if row is None else self._row_to_item(row)

    def change_total_count(
        self, item_id: int, delta: int, remove_if_zero: bool = False
    ) -> InventoryItem | None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE inventory_items
                    SET count = count + %s, updated_at = NOW()
                    WHERE id = %s AND count + %s >= 0
                    """,
                    (delta, item_id, delta),
                )
                if cursor.rowcount == 0:
                    return None
        return self.get(item_id)

    def remove(self, item_id: int) -> bool:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM inventory_items WHERE id = %s", (item_id,))
                return cursor.rowcount > 0

    def set_checked_out(
        self, item_id: int, checked_out: bool
    ) -> InventoryItem | None:
        with self._connect(self.config.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE inventory_items
                    SET checked_out = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (checked_out, item_id),
                )
                if cursor.rowcount == 0:
                    return None
        return self.get(item_id)

    @staticmethod
    def _select_sql() -> LiteralString:
        return """
            SELECT i.id, i.name, i.description, i.count,
                   i.location_id, l.name, i.sub_location_id, sl.name,
                   i.checked_out, i.created_at, i.updated_at
            FROM inventory_items i
            LEFT JOIN inventory_locations l ON l.id = i.location_id
            LEFT JOIN inventory_sub_locations sl ON sl.id = i.sub_location_id
        """

    @staticmethod
    def _row_to_item(row: tuple[Any, ...]) -> InventoryItem:
        location = (
            Location(id=row[4], name=row[5])
            if row[4] is not None
            else None
        )
        sub_location = (
            SubLocation(id=row[6], location_id=row[4], name=row[7])
            if row[6] is not None
            else None
        )
        return InventoryItem(
            id=row[0],
            name=row[1],
            description=row[2],
            count=row[3],
            location=location,
            sub_location=sub_location,
            checked_out=row[8],
            created_at=row[9],
            updated_at=row[10],
        )
