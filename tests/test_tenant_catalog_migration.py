import importlib
import unittest
from unittest.mock import MagicMock, patch


migration = importlib.import_module(
    "migrations.versions.a06e8f4b7c19_tenant_scope_clinical_catalogs"
)


class TenantCatalogMigrationTests(unittest.TestCase):
    def test_constraint_backing_index_is_not_dropped_twice(self):
        inspector = MagicMock()
        inspector.get_unique_constraints.return_value = [
            {
                "name": "lab_tests_code_key",
                "column_names": ["code"],
            }
        ]
        inspector.get_indexes.return_value = [
            {
                "name": "lab_tests_code_key",
                "column_names": ["code"],
                "unique": True,
                "duplicates_constraint": "lab_tests_code_key",
            }
        ]
        batch_operation = MagicMock()
        batch_context = MagicMock()
        batch_context.__enter__.return_value = batch_operation

        with patch.object(migration.op, "get_bind", return_value=object()), patch.object(
            migration,
            "inspect",
            return_value=inspector,
        ), patch.object(
            migration.op,
            "batch_alter_table",
            return_value=batch_context,
        ), patch.object(migration.op, "drop_index") as drop_index:
            migration._drop_global_code_uniqueness("lab_tests")

        batch_operation.drop_constraint.assert_called_once_with(
            "lab_tests_code_key",
            type_="unique",
        )
        drop_index.assert_not_called()

    def test_standalone_unique_index_is_dropped(self):
        inspector = MagicMock()
        inspector.get_unique_constraints.return_value = []
        inspector.get_indexes.return_value = [
            {
                "name": "ix_lab_tests_code_unique",
                "column_names": ["code"],
                "unique": True,
            }
        ]

        with patch.object(migration.op, "get_bind", return_value=object()), patch.object(
            migration,
            "inspect",
            return_value=inspector,
        ), patch.object(migration.op, "drop_index") as drop_index:
            migration._drop_global_code_uniqueness("lab_tests")

        drop_index.assert_called_once_with(
            "ix_lab_tests_code_unique",
            table_name="lab_tests",
        )


if __name__ == "__main__":
    unittest.main()
