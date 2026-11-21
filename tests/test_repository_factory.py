import os
import unittest
from unittest.mock import patch

from service import DatabaseConfig, create_inventory_repository_from_env


class CreateInventoryRepositoryTests(unittest.TestCase):
    def test_selects_configured_postgres_backend(self) -> None:
        environment = {
            "STORAGE_TRACK_BACKEND": "POSTGRES",
            "STORAGE_TRACK_DB_HOST": "db",
            "STORAGE_TRACK_DB_PORT": "5433",
            "STORAGE_TRACK_DB_NAME": "inventory",
            "STORAGE_TRACK_DB_USER": "app",
            "STORAGE_TRACK_DB_PASSWORD": "secret",
        }
        config = DatabaseConfig(
            host="db",
            port=5433,
            database="inventory",
            user="app",
            password="secret",
        )
        with patch.dict(os.environ, environment, clear=True):
            with patch(
                "service.repository_factory.PostgresInventoryRepository"
            ) as postgres_repository:
                repository = create_inventory_repository_from_env()

        self.assertIs(repository, postgres_repository.return_value)
        postgres_repository.assert_called_once_with(config)

    def test_selects_postgres_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "service.repository_factory.PostgresInventoryRepository"
            ) as postgres_repository:
                repository = create_inventory_repository_from_env()

        self.assertIs(repository, postgres_repository.return_value)
        postgres_repository.assert_called_once_with(DatabaseConfig())

    def test_rejects_unsupported_backend(self) -> None:
        with patch.dict(os.environ, {"STORAGE_TRACK_BACKEND": "mongodb"}, clear=True):
            with self.assertRaisesRegex(
                ValueError, "unsupported STORAGE_TRACK_BACKEND 'mongodb'"
            ):
                create_inventory_repository_from_env()
