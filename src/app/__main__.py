import os

from service.grpc_client import GrpcInventoryClient
from . import create_app


def main() -> None:
    service = GrpcInventoryClient(
        address=os.getenv("STORAGE_TRACK_SERVICE_ADDRESS", "localhost:50051"),
        timeout=float(os.getenv("STORAGE_TRACK_SERVICE_TIMEOUT", "5")),
    )
    try:
        app = create_app(service)
        app.run(
            host=os.getenv("STORAGE_TRACK_HOST", "0.0.0.0"),
            port=int(os.getenv("STORAGE_TRACK_PORT", "5000")),
        )
    finally:
        service.close()


if __name__ == "__main__":
    main()
