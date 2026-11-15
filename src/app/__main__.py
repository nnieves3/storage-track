import os

from service import InventoryService, create_inventory_repository_from_env
from . import create_app


def main() -> None:
    service = InventoryService(create_inventory_repository_from_env())
    service.initialize()

    app = create_app(service)
    app.run(
        host=os.getenv("STORAGE_TRACK_HOST", "0.0.0.0"),
        port=int(os.getenv("STORAGE_TRACK_PORT", "5000")),
    )


if __name__ == "__main__":
    main()
