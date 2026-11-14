# storage-track

`storage-track` tracks physical items with a REST API and a separate inventory
service. The API lives in `app`; inventory models and operations live in
`service`. Storage contracts and implementations live in `data`, with
PostgreSQL provided as the default implementation.

## Install

```bash
python3 -m pip install -e .
```

## Basic usage

```python
from data import DatabaseConfig, PostgresInventoryRepository
from service import InventoryService

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
from data import InventoryRepository
from service import InventoryService


class MyInventoryRepository:
    # Implement the operations declared by InventoryRepository.
    ...


inventory = InventoryService(MyInventoryRepository())
```

The protocol defines storage operations for items, locations, and sub-locations.
Any backend (for example MySQL, a document database, or a pandas-backed
spreadsheet) should implement that complete contract and preserve the inventory
validation and relationship behavior expected by the service. Backend-specific
configuration and dependencies belong in that implementation; the core package
does not select a backend automatically.

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

Install and start with the package's Flask dependency:

```bash
python3 -m pip install -e .
storage-track-api
```

The launcher initializes the configured repository before serving the API.
Set `STORAGE_TRACK_DB_HOST`, `STORAGE_TRACK_DB_PORT`,
`STORAGE_TRACK_DB_NAME`, `STORAGE_TRACK_DB_USER`, and
`STORAGE_TRACK_DB_PASSWORD` to configure PostgreSQL. The HTTP listener defaults
to `0.0.0.0:5000`; override it with `STORAGE_TRACK_HOST` and
`STORAGE_TRACK_PORT`.

Available endpoints:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/items` | List items |
| `GET` | `/items/<id>` | Get an item |
| `POST` | `/items` | Add or increment an item |
| `DELETE` | `/items/<id>?count=N` | Reduce an item count; omit `count` to reduce by 1, or use `0` to remove it |
| `POST` | `/items/<id>/checkout` | Mark the item as checked out |
| `POST` | `/items/<id>/checkin` | Mark the item as not checked out |
| `PATCH` | `/items/<id>/move` | Change general and specific locations |

Example add request:

```bash
curl -X POST http://127.0.0.1:5000/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"Camping lantern","count":2,"general_location":"Garage","specific_location":"Shelf B"}'
```