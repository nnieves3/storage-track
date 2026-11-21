import unittest
from concurrent import futures
from datetime import datetime, timezone
from unittest.mock import Mock

import grpc

from app import create_app
from service import InventoryItem, InventoryService, Location, SubLocation
from service import inventory_pb2_grpc as pb_grpc
from service.grpc_client import GrpcInventoryClient, ServiceUnavailableError
from service.grpc_server import InventoryGrpcServicer


class GrpcInventoryClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = Mock(spec=InventoryService)
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        pb_grpc.add_InventoryServicer_to_server(
            InventoryGrpcServicer(self.service), self.server
        )
        port = self.server.add_insecure_port("127.0.0.1:0")
        self.server.start()
        self.client = GrpcInventoryClient(f"127.0.0.1:{port}")

    def tearDown(self) -> None:
        self.client.close()
        self.server.stop(grace=0).wait()

    def test_round_trips_item_and_sends_optional_location_ids(self) -> None:
        expected = InventoryItem(
            id=12,
            name="Lantern",
            description="LED",
            count=3,
            location=Location(
                id=4,
                name="Garage",
                sub_locations=[SubLocation(id=7, name="Shelf", location_id=4)],
            ),
            sub_location=SubLocation(id=7, name="Shelf", location_id=4),
            checked_out=True,
            created_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )
        self.service.add_or_increment_item.return_value = expected

        result = self.client.add_or_increment_item(
            "Lantern", count=3, description="LED", location_id=4, sub_location_id=7
        )

        self.assertEqual(result, expected)
        self.service.add_or_increment_item.assert_called_once_with(
            name="Lantern",
            count=3,
            description="LED",
            location_id=4,
            sub_location_id=7,
        )

    def test_missing_item_is_returned_as_none(self) -> None:
        self.service.get_item.return_value = None

        self.assertIsNone(self.client.get_item(404))

    def test_invalid_operation_is_returned_as_value_error(self) -> None:
        self.service.create_location.side_effect = ValueError("name is required")

        with self.assertRaisesRegex(ValueError, "name is required"):
            self.client.create_location("")

    def test_optional_location_ids_remain_absent_when_not_supplied(self) -> None:
        self.service.add_or_increment_item.return_value = InventoryItem(name="Box")

        self.client.add_or_increment_item("Box")

        self.service.add_or_increment_item.assert_called_once_with(
            name="Box",
            count=1,
            description="",
            location_id=None,
            sub_location_id=None,
        )

    def test_rest_reports_unavailable_inventory_service_as_503(self) -> None:
        api_service = Mock()
        api_service.list_items.side_effect = ServiceUnavailableError("service offline")

        response = create_app(api_service).test_client().get("/items")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "service offline"})

    def test_sub_location_without_location_is_rejected_before_repository_calls(
        self,
    ) -> None:
        repository = Mock()
        service = InventoryService(repository)

        with self.assertRaisesRegex(ValueError, "location_id is required"):
            service.add_item("Box", sub_location_id=3)
        with self.assertRaisesRegex(ValueError, "location_id is required"):
            service.add_or_increment_item("Box", sub_location_id=3)

        repository.add.assert_not_called()
        repository.get_by_name.assert_not_called()


if __name__ == "__main__":
    unittest.main()
