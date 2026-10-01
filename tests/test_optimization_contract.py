"""Regression checks for the optimized Home Assistant integration."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "state_grid_info"


class OptimizationContractTests(unittest.TestCase):
    def test_duplicate_five_minute_task_is_removed(self) -> None:
        source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        self.assertNotIn("asyncio.sleep(300)", source)
        self.assertNotIn("refresh_data_periodically", source)

    def test_coordinator_suppresses_unchanged_data(self) -> None:
        source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        self.assertIn("always_update=False", source)
        self.assertIn("CoordinatorEntity[StateGridInfoDataCoordinator]", source)
        self.assertIn("self._attr_should_poll = False", source)
        self.assertIn("call_soon_threadsafe", source)

    def test_manifest_and_translations_are_valid_json(self) -> None:
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "4.3.0")
        for path in [
            COMPONENT / "strings.json",
            COMPONENT / "translations" / "zh-Hans.json",
            COMPONENT / "translations" / "en.json",
        ]:
            json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
