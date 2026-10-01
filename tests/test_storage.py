"""Tests for State Grid persistent storage."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
STORAGE_PATH = ROOT / "custom_components" / "state_grid_info" / "storage.py"
SPEC = importlib.util.spec_from_file_location("state_grid_storage", STORAGE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
StateGridStorage = MODULE.StateGridStorage


class FakeConfig:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, name: str) -> str:
        return str(self.root / name)


class FakeHass:
    def __init__(self, root: Path) -> None:
        self.config = FakeConfig(root)


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = StateGridStorage(FakeHass(self.root), "123")
        self.storage._load_sync()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_identical_data_does_not_write_again(self) -> None:
        payload = {
            "date": "2026-08-10",
            "balance": 602.44,
            "consumer_name": "test",
            "dayList": [{"day": "2026-08-09", "dayElePq": 1.2}],
            "monthList": [{"month": "2026-08", "monthElePq": 3.4}],
            "yearList": [{"year": "2026", "yearElePq": 5.6}],
        }

        with patch.object(self.storage, "_save_sync") as save:
            first = self.storage.update(payload)
            second = self.storage.update(payload)

        self.assertEqual(first, second)
        self.assertEqual(save.call_count, 1)

    def test_returned_snapshot_cannot_mutate_internal_data(self) -> None:
        snapshot = self.storage.update(
            {"dayList": [{"day": "2026-08-09", "dayElePq": 1.2}]}
        )
        snapshot["dayList"][0]["dayElePq"] = 99
        self.assertEqual(self.storage.data["dayList"][0]["dayElePq"], 1.2)

    def test_atomic_file_contains_valid_json(self) -> None:
        self.storage.update({"balance": 100.5})
        path = self.root / "state_grid_info_123.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["balance"], 100.5)
        self.assertFalse(Path(f"{path}.tmp").exists())

    def test_invalid_list_rows_are_ignored(self) -> None:
        result = self.storage.update(
            {"dayList": [{"day": "2026-08-09"}, {"bad": "row"}, None]}
        )
        self.assertEqual(result["dayList"], [{"day": "2026-08-09"}])


if __name__ == "__main__":
    unittest.main()
