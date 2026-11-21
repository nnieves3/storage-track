from typing import Protocol

from flask import Flask, Response, jsonify, request

from service import InventoryItem, Location, SubLocation
from service.grpc_client import ServiceUnavailableError


class InventoryApi(Protocol):
    def list_items(self) -> list[InventoryItem]: ...
    def get_item(self, item_id: int) -> InventoryItem | None: ...
    def add_or_increment_item(
        self,
        name: str,
        count: int = 1,
        description: str = "",
        location_id: int | None = None,
        sub_location_id: int | None = None,
    ) -> InventoryItem: ...
    def remove_item_quantity(
        self, item_id: int, quantity: int = 1
    ) -> InventoryItem | None: ...
    def check_out(self, item_id: int) -> InventoryItem | None: ...
    def check_in(self, item_id: int) -> InventoryItem | None: ...
    def move_item(
        self, item_id: int, location_id: int, sub_location_id: int | None = None
    ) -> InventoryItem | None: ...
    def list_locations(self) -> list[Location]: ...
    def get_location(self, location_id: int) -> Location | None: ...
    def create_location(self, name: str) -> Location: ...
    def remove_location(self, location_id: int) -> bool: ...
    def create_sub_location(
        self, location_id: int, name: str
    ) -> SubLocation | None: ...
    def remove_sub_location(
        self, location_id: int, sub_location_id: int
    ) -> bool: ...


def create_app(service: InventoryApi) -> Flask:
    app = Flask(__name__)

    @app.errorhandler(ServiceUnavailableError)
    def handle_service_unavailable(
        error: ServiceUnavailableError,
    ) -> tuple[Response, int]:
        return jsonify(error=str(error)), 503

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError) -> tuple[Response, int]:
        return jsonify(error=str(error)), 400

    def json_body() -> dict[str, object]:
        body = request.get_json(silent=True)
        if body is None:
            return {}
        if not isinstance(body, dict):
            raise ValueError("JSON body must be an object")
        return body

    def positive_int(body: dict[str, object], key: str = "count", default: int = 1) -> int:
        value = body.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be an integer")
        if value <= 0:
            raise ValueError(f"{key} must be positive")
        return value

    @app.get("/health")
    def health() -> tuple[Response, int]:
        return jsonify(status="ok"), 200

    @app.get("/items")
    def list_items() -> tuple[Response, int]:
        return jsonify([item.to_dict() for item in service.list_items()]), 200

    @app.get("/items/<int:item_id>")
    def get_item(item_id: int) -> tuple[Response, int]:
        item = service.get_item(item_id)
        if item is None:
            return jsonify(error="item not found"), 404
        return jsonify(item.to_dict()), 200

    @app.post("/items")
    def add_item() -> tuple[Response, int]:
        body = json_body()
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name is required")
        count = positive_int(body)
        description = body.get("description", "")
        if not isinstance(description, str):
            raise ValueError("description must be a string")
        location_id = body.get("location_id")
        sub_location_id = body.get("sub_location_id")
        if location_id is not None and (
            isinstance(location_id, bool) or not isinstance(location_id, int)
        ):
            raise ValueError("location_id must be an integer")
        if sub_location_id is not None and (
            isinstance(sub_location_id, bool) or not isinstance(sub_location_id, int)
        ):
            raise ValueError("sub_location_id must be an integer")
        item = service.add_or_increment_item(
            name=name,
            count=count,
            description=description,
            location_id=location_id,
            sub_location_id=sub_location_id,
        )
        return jsonify(item.to_dict()), 201

    @app.delete("/items/<int:item_id>")
    def remove_item(item_id: int) -> tuple[Response, int]:
        quantity = request.args.get("count", default=1, type=int)
        if quantity is None or quantity < 0:
            raise ValueError("count must be a non-negative integer")
        item = service.remove_item_quantity(item_id, quantity)
        if item is None:
            return jsonify(error="item not found"), 404
        if item.count == 0 and item.id == item_id:
            return Response(status=204), 204
        return jsonify(item.to_dict()), 200

    @app.post("/items/<int:item_id>/checkout")
    def check_out_item(item_id: int) -> tuple[Response, int]:
        item = service.check_out(item_id)
        if item is None:
            return jsonify(error="item not found"), 404
        return jsonify(item.to_dict()), 200

    @app.post("/items/<int:item_id>/checkin")
    def check_in_item(item_id: int) -> tuple[Response, int]:
        item = service.check_in(item_id)
        if item is None:
            return jsonify(error="item not found"), 404
        return jsonify(item.to_dict()), 200

    @app.patch("/items/<int:item_id>/move")
    def move_item(item_id: int) -> tuple[Response, int]:
        body = json_body()
        location_id = body.get("location_id")
        sub_location_id = body.get("sub_location_id")
        if isinstance(location_id, bool) or not isinstance(location_id, int):
            raise ValueError("location_id is required")
        if sub_location_id is not None and (
            isinstance(sub_location_id, bool) or not isinstance(sub_location_id, int)
        ):
            raise ValueError("sub_location_id must be an integer")
        item = service.move_item(
            item_id,
            location_id=location_id,
            sub_location_id=sub_location_id,
        )
        if item is None:
            return jsonify(error="item not found"), 404
        return jsonify(item.to_dict()), 200

    @app.get("/locations")
    def list_locations() -> tuple[Response, int]:
        return jsonify([location.to_dict() for location in service.list_locations()]), 200

    @app.get("/locations/<int:location_id>")
    def get_location(location_id: int) -> tuple[Response, int]:
        location = service.get_location(location_id)
        if location is None:
            return jsonify(error="location not found"), 404
        return jsonify(location.to_dict()), 200

    @app.post("/locations")
    def create_location() -> tuple[Response, int]:
        body = json_body()
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name is required")
        location = service.create_location(name)
        return jsonify(location.to_dict()), 201

    @app.delete("/locations/<int:location_id>")
    def remove_location(location_id: int) -> tuple[Response, int]:
        if not service.remove_location(location_id):
            return jsonify(error="location not found"), 404
        return Response(status=204), 204

    @app.post("/locations/<int:location_id>/sub-locations")
    def create_sub_location(location_id: int) -> tuple[Response, int]:
        body = json_body()
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name is required")
        sub_location = service.create_sub_location(location_id, name)
        if sub_location is None:
            return jsonify(error="location not found"), 404
        return jsonify(sub_location.to_dict()), 201

    @app.delete("/locations/<int:location_id>/sub-locations/<int:sub_location_id>")
    def remove_sub_location(
        location_id: int, sub_location_id: int
    ) -> tuple[Response, int]:
        if not service.remove_sub_location(location_id, sub_location_id):
            return jsonify(error="sub-location not found"), 404
        return Response(status=204), 204

    return app