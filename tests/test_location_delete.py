import unittest
from unittest.mock import Mock

from service.database import DatabaseConfig, PostgresInventoryRepository


class PostgresLocationDeleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Mock()
        self.cursor.__enter__ = Mock(return_value=self.cursor)
        self.cursor.__exit__ = Mock(return_value=False)
        self.connection = Mock()
        self.connection.__enter__ = Mock(return_value=self.connection)
        self.connection.__exit__ = Mock(return_value=False)
        self.connection.cursor.return_value = self.cursor
        self.cursor.rowcount = 1
        self.connect = Mock(return_value=self.connection)
        self.repository = PostgresInventoryRepository(
            DatabaseConfig(), connection_factory=self.connect
        )
        self.cursor.fetchone.side_effect = [(4,), (2,)]

    def test_cascade_deletes_items_before_sub_locations_and_location(self) -> None:
        self.assertTrue(self.repository.remove_location(4, cascade=True))

        statements = [
            call.args[0]
            for call in self.cursor.execute.call_args_list
        ]
        delete_item_index = next(
            index
            for index, statement in enumerate(statements)
            if "DELETE FROM inventory_items" in statement
        )
        delete_sub_location_index = next(
            index
            for index, statement in enumerate(statements)
            if "DELETE FROM inventory_sub_locations" in statement
        )
        delete_location_index = next(
            index
            for index, statement in enumerate(statements)
            if "DELETE FROM inventory_locations" in statement
        )

        self.assertLess(delete_item_index, delete_sub_location_index)
        self.assertLess(delete_sub_location_index, delete_location_index)

    def test_non_cascade_delete_refuses_assigned_items(self) -> None:
        with self.assertRaisesRegex(ValueError, "items are assigned"):
            self.repository.remove_location(4)

        self.assertEqual(self.cursor.execute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
