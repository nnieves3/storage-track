import os

from .database import DatabaseConfig, PostgresInventoryRepository
from .repository import InventoryRepository


def create_inventory_repository_from_env() -> InventoryRepository:
    backend = os.getenv("STORAGE_TRACK_BACKEND", "postgres").strip().lower()
    if backend != "postgres":
        raise ValueError(
            f"unsupported STORAGE_TRACK_BACKEND {backend!r}; "
            "supported backends: postgres"
        )

    config = DatabaseConfig(
        host=os.getenv("STORAGE_TRACK_DB_HOST", "localhost"),
        port=int(os.getenv("STORAGE_TRACK_DB_PORT", "5432")),
        database=os.getenv("STORAGE_TRACK_DB_NAME", "storage_track"),
        user=os.getenv("STORAGE_TRACK_DB_USER", "postgres"),
        password=os.getenv("STORAGE_TRACK_DB_PASSWORD"),
    )
    return PostgresInventoryRepository(config)
