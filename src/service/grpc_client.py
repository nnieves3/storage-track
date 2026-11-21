from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message

from . import inventory_pb2 as pb
from . import inventory_pb2_grpc as pb_grpc
from .models import InventoryItem, Location, SubLocation

_Response = TypeVar("_Response", bound=Message)


class ServiceUnavailableError(RuntimeError):
    """The inventory gRPC service could not complete a request."""


def _from_proto_sub_location(value: pb.SubLocation) -> SubLocation:
    return SubLocation(
        name=value.name,
        id=value.id if value.HasField("id") else None,
        location_id=value.location_id if value.HasField("location_id") else None,
    )


def _from_proto_location(value: pb.Location) -> Location:
    return Location(
        name=value.name,
        id=value.id if value.HasField("id") else None,
        sub_locations=[_from_proto_sub_location(item) for item in value.sub_locations],
    )


def _parse_datetime(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _from_proto_item(value: pb.Item) -> InventoryItem:
    return InventoryItem(
        name=value.name,
        description=value.description,
        count=value.count,
        location=(
            _from_proto_location(value.location)
            if value.HasField("location")
            else None
        ),
        sub_location=(
            _from_proto_sub_location(value.sub_location)
            if value.HasField("sub_location")
            else None
        ),
        id=value.id if value.HasField("id") else None,
        checked_out=value.checked_out,
        created_at=_parse_datetime(value.created_at),
        updated_at=_parse_datetime(value.updated_at),
    )


class GrpcInventoryClient:
    def __init__(self, address: str, timeout: float = 5.0) -> None:
        self._channel = grpc.insecure_channel(address)
        self._stub = pb_grpc.InventoryStub(self._channel)
        self._timeout = timeout

    def close(self) -> None:
        self._channel.close()

    def _call(
        self,
        rpc: Callable[..., _Response],
        request: Message,
    ) -> _Response:
        try:
            return rpc(request, timeout=self._timeout)
        except grpc.RpcError as error:
            code = error.code()
            details = error.details() or "inventory service request failed"
            if code == grpc.StatusCode.INVALID_ARGUMENT:
                raise ValueError(details) from error
            if code == grpc.StatusCode.NOT_FOUND:
                raise _RemoteNotFound(details) from error
            if code in (
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED,
            ):
                raise ServiceUnavailableError(details) from error
            raise RuntimeError(f"inventory service error ({code.name}): {details}") from error

    def list_items(self) -> list[InventoryItem]:
        response = self._call(self._stub.ListItems, Empty())
        assert isinstance(response, pb.ListItemsResponse)
        return [_from_proto_item(item) for item in response.items]

    def get_item(self, item_id: int) -> InventoryItem | None:
        try:
            response = self._call(self._stub.GetItem, pb.IdRequest(id=item_id))
        except _RemoteNotFound:
            return None
        assert isinstance(response, pb.Item)
        return _from_proto_item(response)

    def add_or_increment_item(
        self,
        name: str,
        count: int = 1,
        description: str = "",
        location_id: int | None = None,
        sub_location_id: int | None = None,
    ) -> InventoryItem:
        request = pb.AddItemRequest(name=name, count=count, description=description)
        if location_id is not None:
            request.location_id = location_id
        if sub_location_id is not None:
            request.sub_location_id = sub_location_id
        response = self._call(self._stub.AddOrIncrementItem, request)
        assert isinstance(response, pb.Item)
        return _from_proto_item(response)

    def remove_item_quantity(
        self, item_id: int, quantity: int = 1
    ) -> InventoryItem | None:
        try:
            response = self._call(
                self._stub.RemoveItemQuantity,
                pb.RemoveItemRequest(item_id=item_id, quantity=quantity),
            )
        except _RemoteNotFound:
            return None
        assert isinstance(response, pb.Item)
        return _from_proto_item(response)

    def check_out(self, item_id: int) -> InventoryItem | None:
        return self._item_or_none(self._stub.CheckOut, item_id)

    def check_in(self, item_id: int) -> InventoryItem | None:
        return self._item_or_none(self._stub.CheckIn, item_id)

    def _item_or_none(
        self, rpc: Callable[..., _Response], item_id: int
    ) -> InventoryItem | None:
        try:
            response = self._call(rpc, pb.IdRequest(id=item_id))
        except _RemoteNotFound:
            return None
        assert isinstance(response, pb.Item)
        return _from_proto_item(response)

    def move_item(
        self,
        item_id: int,
        location_id: int,
        sub_location_id: int | None = None,
    ) -> InventoryItem | None:
        request = pb.MoveItemRequest(item_id=item_id, location_id=location_id)
        if sub_location_id is not None:
            request.sub_location_id = sub_location_id
        try:
            response = self._call(self._stub.MoveItem, request)
        except _RemoteNotFound:
            return None
        assert isinstance(response, pb.Item)
        return _from_proto_item(response)

    def list_locations(self) -> list[Location]:
        response = self._call(self._stub.ListLocations, Empty())
        assert isinstance(response, pb.ListLocationsResponse)
        return [_from_proto_location(item) for item in response.locations]

    def get_location(self, location_id: int) -> Location | None:
        try:
            response = self._call(
                self._stub.GetLocation, pb.IdRequest(id=location_id)
            )
        except _RemoteNotFound:
            return None
        assert isinstance(response, pb.Location)
        return _from_proto_location(response)

    def create_location(self, name: str) -> Location:
        response = self._call(self._stub.CreateLocation, pb.NameRequest(name=name))
        assert isinstance(response, pb.Location)
        return _from_proto_location(response)

    def remove_location(self, location_id: int, cascade: bool = False) -> bool:
        response = self._call(
            self._stub.RemoveLocation,
            pb.RemoveLocationRequest(id=location_id, cascade=cascade),
        )
        assert isinstance(response, pb.RemoveResponse)
        return response.removed

    def create_sub_location(
        self, location_id: int, name: str
    ) -> SubLocation | None:
        try:
            response = self._call(
                self._stub.CreateSubLocation,
                pb.CreateSubLocationRequest(location_id=location_id, name=name),
            )
        except _RemoteNotFound:
            return None
        assert isinstance(response, pb.SubLocation)
        return _from_proto_sub_location(response)

    def remove_sub_location(
        self, location_id: int, sub_location_id: int
    ) -> bool:
        response = self._call(
            self._stub.RemoveSubLocation,
            pb.RemoveSubLocationRequest(
                location_id=location_id, sub_location_id=sub_location_id
            ),
        )
        assert isinstance(response, pb.RemoveResponse)
        return response.removed


class _RemoteNotFound(Exception):
    pass
