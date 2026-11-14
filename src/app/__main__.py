import os

from data import DatabaseConfig, PostgresInventoryRepository
from service import InventoryService
from . import create_app


def main() -> None:
    config = DatabaseConfig(
        host=os.getenv("STORAGE_TRACK_DB_HOST", "localhost"),
        port=int(os.getenv("STORAGE_TRACK_DB_PORT", "5432")),
        database=os.getenv("STORAGE_TRACK_DB_NAME", "storage_track"),
        user=os.getenv("STORAGE_TRACK_DB_USER", "postgres"),
        password=os.getenv("STORAGE_TRACK_DB_PASSWORD"),
    )
    service = InventoryService(PostgresInventoryRepository(config))
    service.initialize()

    app = create_app(service)
    app.run(
        host=os.getenv("STORAGE_TRACK_HOST", "0.0.0.0"),
        port=int(os.getenv("STORAGE_TRACK_PORT", "5000")),
    )


if __name__ == "__main__":
    main()
