from __future__ import annotations

import os
from collections.abc import Callable
from concurrent import futures
from typing import TypeVar

import grpc
from google.protobuf.empty_pb2 import Empty

from . import inventory_pb2 as pb
from . import inventory_pb2_grpc as pb_grpc
from .models import InventoryItem, Location, SubLocation
from .repository_factory import create_inventory_repository_from_env
from .service import InventoryService

_T = TypeVar("_T")


def _run(context: grpc.ServicerContext, operation: Callable[[], _T]) -> _T:
    try:
        return operation()
    except ValueError as error:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
    except LookupError as error:
        context.abort(grpc.StatusCode.NOT_FOUND, str(error))


def _to_proto_sub_location(value: SubLocation) -> pb.SubLocation:
    result = pb.SubLocation(name=value.name)
    if value.id is not None:
        result.id = value.id
    if value.location_id is not None:
        result.location_id = value.location_id
    return result


def _to_proto_location(value: Location) -> pb.Location:
    result = pb.Location(name=value.name)
    if value.id is not None:
        result.id = value.id
    result.sub_locations.extend(
        _to_proto_sub_location(item) for item in (value.sub_locations or [])
    )
    return result


def _to_proto_item(value: InventoryItem) -> pb.Item:
    result = pb.Item(
        name=value.name,
        description=value.description,
        count=value.count,
        checked_out=value.checked_out,
        created_at=value.created_at.isoformat() if value.created_at else "",
        updated_at=value.updated_at.isoformat() if value.updated_at else "",
    )
    if value.id is not None:
        result.id = value.id
    if value.location is not None:
        result.location.CopyFrom(_to_proto_location(value.location))
    if value.sub_location is not None:
        result.sub_location.CopyFrom(_to_proto_sub_location(value.sub_location))
    return result


class InventoryGrpcServicer(pb_grpc.InventoryServicer):
    def __init__(self, service: InventoryService) -> None:
        self._service = service

    def ListItems(
        self, request: Empty, context: grpc.ServicerContext
    ) -> pb.ListItemsResponse:
        _ = request
        return _run(
            context,
            lambda: pb.ListItemsResponse(
                items=[_to_proto_item(item) for item in self._service.list_items()]
            ),
        )

    def GetItem(self, request: pb.IdRequest, context: grpc.ServicerContext) -> pb.Item:
        item = _run(context, lambda: self._service.get_item(request.id))
        if item is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "item not found")
        return _to_proto_item(item)

    def AddOrIncrementItem(
        self, request: pb.AddItemRequest, context: grpc.ServicerContext
    ) -> pb.Item:
        return _run(
            context,
            lambda: _to_proto_item(
                self._service.add_or_increment_item(
                    name=request.name,
                    count=request.count,
                    description=request.description,
                    location_id=request.location_id if request.HasField("location_id") else None,
                    sub_location_id=(
                        request.sub_location_id
                        if request.HasField("sub_location_id")
                        else None
                    ),
                )
            ),
        )

    def RemoveItemQuantity(
        self, request: pb.RemoveItemRequest, context: grpc.ServicerContext
    ) -> pb.Item:
        item = _run(
            context,
            lambda: self._service.remove_item_quantity(
                request.item_id, request.quantity
            ),
        )
        if item is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "item not found")
        return _to_proto_item(item)

    def CheckOut(self, request: pb.IdRequest, context: grpc.ServicerContext) -> pb.Item:
        item = _run(context, lambda: self._service.check_out(request.id))
        if item is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "item not found")
        return _to_proto_item(item)

    def CheckIn(self, request: pb.IdRequest, context: grpc.ServicerContext) -> pb.Item:
        item = _run(context, lambda: self._service.check_in(request.id))
        if item is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "item not found")
        return _to_proto_item(item)

    def MoveItem(
        self, request: pb.MoveItemRequest, context: grpc.ServicerContext
    ) -> pb.Item:
        item = _run(
            context,
            lambda: self._service.move_item(
                request.item_id,
                request.location_id,
                request.sub_location_id
                if request.HasField("sub_location_id")
                else None,
            ),
        )
        if item is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "item not found")
        return _to_proto_item(item)

    def ListLocations(
        self, request: Empty, context: grpc.ServicerContext
    ) -> pb.ListLocationsResponse:
        _ = request
        return _run(
            context,
            lambda: pb.ListLocationsResponse(
                locations=[
                    _to_proto_location(location)
                    for location in self._service.list_locations()
                ]
            ),
        )

    def GetLocation(
        self, request: pb.IdRequest, context: grpc.ServicerContext
    ) -> pb.Location:
        location = _run(context, lambda: self._service.get_location(request.id))
        if location is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "location not found")
        return _to_proto_location(location)

    def CreateLocation(
        self, request: pb.NameRequest, context: grpc.ServicerContext
    ) -> pb.Location:
        return _run(
            context,
            lambda: _to_proto_location(self._service.create_location(request.name)),
        )

    def RemoveLocation(
        self, request: pb.IdRequest, context: grpc.ServicerContext
    ) -> pb.RemoveResponse:
        return _run(
            context,
            lambda: pb.RemoveResponse(
                removed=self._service.remove_location(request.id)
            ),
        )

    def CreateSubLocation(
        self, request: pb.CreateSubLocationRequest, context: grpc.ServicerContext
    ) -> pb.SubLocation:
        sub_location = _run(
            context,
            lambda: self._service.create_sub_location(
                request.location_id, request.name
            ),
        )
        if sub_location is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "location not found")
        return _to_proto_sub_location(sub_location)

    def RemoveSubLocation(
        self, request: pb.RemoveSubLocationRequest, context: grpc.ServicerContext
    ) -> pb.RemoveResponse:
        return _run(
            context,
            lambda: pb.RemoveResponse(
                removed=self._service.remove_sub_location(
                    request.location_id, request.sub_location_id
                )
            ),
        )


def main() -> None:
    service = InventoryService(create_inventory_repository_from_env())
    service.initialize()

    server = grpc.server(
        futures.ThreadPoolExecutor(
            max_workers=int(os.getenv("STORAGE_TRACK_GRPC_WORKERS", "10"))
        )
    )
    pb_grpc.add_InventoryServicer_to_server(InventoryGrpcServicer(service), server)
    host = os.getenv("STORAGE_TRACK_GRPC_HOST", "0.0.0.0")
    port = int(os.getenv("STORAGE_TRACK_GRPC_PORT", "50051"))
    if server.add_insecure_port(f"{host}:{port}") == 0:
        raise RuntimeError(f"could not bind gRPC server to {host}:{port}")
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=5).wait()


if __name__ == "__main__":
    main()
