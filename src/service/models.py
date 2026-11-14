from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class SubLocation:
    name: str
    id: int | None = None
    location_id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("sub-location name is required")

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "location_id": self.location_id}


@dataclass(slots=True)
class Location:
    name: str
    id: int | None = None
    sub_locations: list[SubLocation] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("location name is required")
        if self.sub_locations is None:
            self.sub_locations = []

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "sub_locations": [item.to_dict() for item in (self.sub_locations or [])],
        }


@dataclass(slots=True)
class InventoryItem:
    name: str
    description: str = ""
    count: int = 1
    location: Location | None = None
    sub_location: SubLocation | None = None
    id: int | None = None
    checked_out: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        if self.count < 0:
            raise ValueError("count cannot be negative")
        if not isinstance(self.checked_out, bool):
            raise ValueError("checked_out must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "count": self.count,
            "location": self.location.to_dict() if self.location else None,
            "sub_location": self.sub_location.to_dict() if self.sub_location else None,
            "checked_out": self.checked_out,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
