# storage-track

`storage-track` tracks physical items with a REST API and a separate gRPC
inventory service. The API lives in `app`; inventory models, operations, and
the gRPC server live in `service`. PostgreSQL is the default storage backend.

## Install

```bash
python3 -m pip install -e '.[postgres]'
```

## Basic usage

```python
from service import (
    DatabaseConfig,
    InventoryService,
    PostgresInventoryRepository,
)

config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="storage_track",
    user="postgres",
    password="change-me",
)
repository = PostgresInventoryRepository(config)
repository.initialize()
inventory = InventoryService(repository)

item = inventory.add_item(
    name="Camping lantern",
    description="Rechargeable LED lantern",
    count=2,
    general_location="Garage",
    specific_location="Shelf B / Bin 3",
)

inventory.check_out(item.id)
inventory.check_in(item.id)
inventory.edit_item(item)
inventory.remove_item(item.id)
```

## Storage backends

`InventoryService` depends on the public `InventoryRepository` protocol rather
than PostgreSQL. `PostgresInventoryRepository` is the included implementation;
you can supply another implementation when constructing the service:

```python
from service import InventoryRepository, InventoryService


class MyInventoryRepository:
    # Implement the operations declared by InventoryRepository.
    ...


inventory = InventoryService(MyInventoryRepository())
```

The protocol defines storage operations for items, locations, and sub-locations.
Any backend (for example MySQL or a document database) should implement that
complete contract and preserve the inventory validation and relationship
behavior expected by the service. The gRPC service launcher selects the adapter with
`STORAGE_TRACK_BACKEND`; it defaults to `postgres` and fails at startup for an
unsupported value. Backend-specific configuration and dependencies belong in
the corresponding adapter.

## Locations

Create a location and its default `Other` sub-location:

```bash
curl -X POST http://127.0.0.1:5000/locations \
  -H 'Content-Type: application/json' \
  -d '{"name":"Pantry"}'
```

Add more sub-locations:

```bash
curl -X POST http://127.0.0.1:5000/locations/1/sub-locations \
  -H 'Content-Type: application/json' \
  -d '{"name":"Shelf 1"}'
```

Items use location objects returned by the API. Add or move an item by IDs:

```bash
curl -X POST http://127.0.0.1:5000/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"Flour","count":1,"location_id":1,"sub_location_id":2}'

curl -X PATCH http://127.0.0.1:5000/items/1/move \
  -H 'Content-Type: application/json' \
  -d '{"location_id":1,"sub_location_id":2}'
```

## REST API

Run the API and gRPC service in separate terminals:

```bash
python3 -m pip install -e '.[postgres]'
# Terminal 1
STORAGE_TRACK_DB_HOST=localhost storage-track-service
# Terminal 2
STORAGE_TRACK_SERVICE_ADDRESS=localhost:50051 storage-track-api
```

The gRPC service initializes the configured repository before listening.
Set `STORAGE_TRACK_BACKEND=postgres` to use the PostgreSQL adapter (the only
currently supported backend), and configure it with `STORAGE_TRACK_DB_HOST`,
`STORAGE_TRACK_DB_PORT`, `STORAGE_TRACK_DB_NAME`, `STORAGE_TRACK_DB_USER`, and
`STORAGE_TRACK_DB_PASSWORD`. The gRPC listener defaults to `0.0.0.0:50051`;
override it with `STORAGE_TRACK_GRPC_HOST` and `STORAGE_TRACK_GRPC_PORT`.
The REST API connects to `localhost:50051` by default; override this with
`STORAGE_TRACK_SERVICE_ADDRESS`. Each API call has a five-second gRPC deadline,
configurable with `STORAGE_TRACK_SERVICE_TIMEOUT`. The HTTP listener defaults
to `0.0.0.0:5000`; override it with `STORAGE_TRACK_HOST` and
`STORAGE_TRACK_PORT`.

### Docker Compose

Build and run the API, inventory service, and PostgreSQL in separate containers:

```bash
docker compose up --build -d
```

The REST API is available at `http://localhost:5000`; only it is published on
the host. Compose waits for PostgreSQL and the gRPC service health checks before
starting dependent containers. The default PostgreSQL password is intended for
local development; set `POSTGRES_PASSWORD` to a secure value outside local use.
Use `docker compose logs -f` to view logs and `docker compose down` to stop the
containers. Add `-v` to `down` only when intentionally deleting the database
volume.

The protocol is defined in `src/service/inventory.proto`; generated Python
stubs are checked in. Regenerate them after editing the protocol:

```bash
python3 -m pip install -e '.[dev]'
python3 -m grpc_tools.protoc -Isrc --python_out=src --grpc_python_out=src --pyi_out=src src/service/inventory.proto
```

Available endpoints:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Check API health |
| `GET` | `/items` | List items |
| `GET` | `/items/<id>` | Get an item |
| `POST` | `/items` | Add or increment an item; optional `location_id` and `sub_location_id` assign its location |
| `DELETE` | `/items/<id>?count=N` | Reduce an item count; omit `count` to reduce by 1, or use `0` to remove it |
| `POST` | `/items/<id>/checkout` | Mark the item as checked out |
| `POST` | `/items/<id>/checkin` | Mark the item as not checked out |
| `PATCH` | `/items/<id>/move` | Move an item using `location_id` and optional `sub_location_id` |
| `GET` | `/locations` | List locations and their sub-locations |
| `GET` | `/locations/<location_id>` | Get a location and its sub-locations |
| `POST` | `/locations` | Create a location (also creates its default `Other` sub-location) |
| `DELETE` | `/locations/<location_id>` | Remove a location if no items are assigned to it |
| `POST` | `/locations/<location_id>/sub-locations` | Create a sub-location |
| `DELETE` | `/locations/<location_id>/sub-locations/<sub_location_id>` | Remove a sub-location if it is not the default and has no assigned items |

Example add request:

```bash
curl -X POST http://127.0.0.1:5000/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"Camping lantern","count":2,"location_id":1,"sub_location_id":2}'
```
