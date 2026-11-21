from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class IdRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class NameRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class AddItemRequest(_message.Message):
    __slots__ = ("name", "count", "description", "location_id", "sub_location_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    SUB_LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    count: int
    description: str
    location_id: int
    sub_location_id: int
    def __init__(self, name: _Optional[str] = ..., count: _Optional[int] = ..., description: _Optional[str] = ..., location_id: _Optional[int] = ..., sub_location_id: _Optional[int] = ...) -> None: ...

class RemoveItemRequest(_message.Message):
    __slots__ = ("item_id", "quantity")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    item_id: int
    quantity: int
    def __init__(self, item_id: _Optional[int] = ..., quantity: _Optional[int] = ...) -> None: ...

class MoveItemRequest(_message.Message):
    __slots__ = ("item_id", "location_id", "sub_location_id")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    SUB_LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    item_id: int
    location_id: int
    sub_location_id: int
    def __init__(self, item_id: _Optional[int] = ..., location_id: _Optional[int] = ..., sub_location_id: _Optional[int] = ...) -> None: ...

class CreateSubLocationRequest(_message.Message):
    __slots__ = ("location_id", "name")
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    location_id: int
    name: str
    def __init__(self, location_id: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class RemoveSubLocationRequest(_message.Message):
    __slots__ = ("location_id", "sub_location_id")
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    SUB_LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    location_id: int
    sub_location_id: int
    def __init__(self, location_id: _Optional[int] = ..., sub_location_id: _Optional[int] = ...) -> None: ...

class RemoveResponse(_message.Message):
    __slots__ = ("removed",)
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    removed: bool
    def __init__(self, removed: _Optional[bool] = ...) -> None: ...

class ListItemsResponse(_message.Message):
    __slots__ = ("items",)
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[Item]
    def __init__(self, items: _Optional[_Iterable[_Union[Item, _Mapping]]] = ...) -> None: ...

class ListLocationsResponse(_message.Message):
    __slots__ = ("locations",)
    LOCATIONS_FIELD_NUMBER: _ClassVar[int]
    locations: _containers.RepeatedCompositeFieldContainer[Location]
    def __init__(self, locations: _Optional[_Iterable[_Union[Location, _Mapping]]] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("id", "name", "description", "count", "location", "sub_location", "checked_out", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    SUB_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CHECKED_OUT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    description: str
    count: int
    location: Location
    sub_location: SubLocation
    checked_out: bool
    created_at: str
    updated_at: str
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., count: _Optional[int] = ..., location: _Optional[_Union[Location, _Mapping]] = ..., sub_location: _Optional[_Union[SubLocation, _Mapping]] = ..., checked_out: _Optional[bool] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ...) -> None: ...

class Location(_message.Message):
    __slots__ = ("id", "name", "sub_locations")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SUB_LOCATIONS_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    sub_locations: _containers.RepeatedCompositeFieldContainer[SubLocation]
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., sub_locations: _Optional[_Iterable[_Union[SubLocation, _Mapping]]] = ...) -> None: ...

class SubLocation(_message.Message):
    __slots__ = ("id", "name", "location_id")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    location_id: int
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., location_id: _Optional[int] = ...) -> None: ...
