from __future__ import annotations

from typing import TYPE_CHECKING

from .models import InventoryItem, Location, SubLocation

if TYPE_CHECKING:
    from data import InventoryRepository


class InventoryService:
    """Application-level inventory operations."""

    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    def initialize(self) -> None:
        self.repository.initialize()

    def add_item(
        self,
        name: str,
        description: str = "",
        count: int = 1,
        location_id: int | None = None,
        sub_location_id: int | None = None,
    ) -> InventoryItem:
        item = InventoryItem(
            name=name,
            description=description,
            count=count,
            location=None,
            sub_location=None,
        )
        item = self.repository.add(item)
        if item.id is not None and (location_id is not None or sub_location_id is not None):
            if location_id is None:
                raise ValueError("location_id is required with sub_location_id")
            moved = self.move_item(item.id, location_id, sub_location_id)
            if moved is not None:
                return moved
        return item

    def add_or_increment_item(
        self,
        name: str,
        count: int = 1,
        description: str = "",
        location_id: int | None = None,
        sub_location_id: int | None = None,
    ) -> InventoryItem:
        if count <= 0:
            raise ValueError("count must be positive")
        existing = self.repository.get_by_name(name)
        if existing is None:
            return self.add_item(
                name=name,
                description=description,
                count=count,
                location_id=location_id,
                sub_location_id=sub_location_id,
            )
        updated = self.repository.change_total_count(existing.id, count)  # type: ignore[arg-type]
        if updated is None:
            raise LookupError(f"inventory item {existing.id} no longer exists")
        if location_id is not None and updated.id is not None:
            moved = self.move_item(updated.id, location_id, sub_location_id)
            if moved is not None:
                return moved
        return updated

    def get_item(self, item_id: int) -> InventoryItem | None:
        return self.repository.get(item_id)

    def list_items(self) -> list[InventoryItem]:
        return self.repository.list()

    def edit_item(self, item: InventoryItem) -> InventoryItem | None:
        item.__post_init__()
        return self.repository.update(item)

    def remove_item(self, item_id: int) -> bool:
        return self.repository.remove(item_id)

    def remove_item_quantity(
        self, item_id: int, quantity: int = 1
    ) -> InventoryItem | None:
        if quantity < 0:
            raise ValueError("removal quantity cannot be negative")
        if quantity == 0:
            if not self.repository.remove(item_id):
                return None
            return InventoryItem(name="", count=0, id=item_id)
        item = self.repository.get(item_id)
        if item is None:
            return None
        if quantity > item.count:
            raise ValueError("removal quantity exceeds item count")
        if quantity == item.count:
            if not self.repository.remove(item_id):
                return None
            return InventoryItem(name="", count=0, id=item_id)
        updated = self.repository.change_total_count(item_id, -quantity)
        if updated is None:
            raise LookupError(f"inventory item {item_id} no longer exists")
        return updated

    def move_item(
        self,
        item_id: int,
        location_id: int,
        sub_location_id: int | None = None,
    ) -> InventoryItem | None:
        item = self.repository.get(item_id)
        if item is None:
            return None
        location = self.repository.get_location(location_id)
        if location is None:
            raise ValueError("location not found")
        if sub_location_id is None:
            matching = next(
                (sub for sub in (location.sub_locations or []) if sub.name == "Other"),
                None,
            )
            if matching is None:
                raise ValueError("location has no Other sub-location")
            sub_location = matching
        else:
            sub_location = self.repository.get_sub_location(sub_location_id)
            if (
                sub_location is None
                or sub_location.location_id != location_id
            ):
                raise ValueError("sub-location not found within location")
        item.location = location
        item.sub_location = sub_location
        return self.repository.update(item)

    def create_location(self, name: str) -> Location:
        return self.repository.create_location(name)

    def get_location(self, location_id: int) -> Location | None:
        return self.repository.get_location(location_id)

    def list_locations(self) -> list[Location]:
        return self.repository.list_locations()

    def remove_location(self, location_id: int) -> bool:
        return self.repository.remove_location(location_id)

    def create_sub_location(
        self, location_id: int, name: str
    ) -> SubLocation | None:
        return self.repository.create_sub_location(location_id, name)

    def remove_sub_location(
        self, location_id: int, sub_location_id: int
    ) -> bool:
        return self.repository.remove_sub_location(location_id, sub_location_id)

    def check_out(self, item_id: int) -> InventoryItem | None:
        return self.repository.set_checked_out(item_id, True)

    def check_in(self, item_id: int) -> InventoryItem | None:
        return self.repository.set_checked_out(item_id, False)
