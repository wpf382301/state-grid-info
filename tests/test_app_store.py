"""Run with Home Assistant installed; all writes use a temporary config directory."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    from homeassistant.core import HomeAssistant
except ImportError:
    HomeAssistant = None
PATH=Path(__file__).parents[1]/'custom_components/state_grid_info/app_store.py'

@unittest.skipIf(HomeAssistant is None,'Home Assistant runtime required')
class AppStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.assertTrue(PATH.exists(),'Native HA archive is not implemented')
        spec=importlib.util.spec_from_file_location('app_store',PATH)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.hass=HomeAssistant(str(self.root))
        self.legacy=self.root/'state_grid_info_test.json'
        self.archive={'date':'2026-09-30','balance':80,'dayList':[{'day':'2025-10-01','dayEleNum':4}], 'monthList':[{'month':'2025-10','monthEleNum':4}], 'yearList':[{'year':'2025','yearEleNum':4}]}
        self.legacy.write_text(json.dumps(self.archive))
    async def asyncTearDown(self):
        if hasattr(self,'hass'): await self.hass.async_stop()
        if hasattr(self,'temp'): self.temp.cleanup()
    async def test_import_survives_restart_and_does_not_reimport_old_file(self):
        store=self.module.AppHistoryStore(self.hass,'test');await store.async_load()
        self.assertEqual(store.data,self.archive)
        updated={**store.data,'balance':90};await store.async_save(updated)
        second=self.module.AppHistoryStore(self.hass,'test');await second.async_load()
        self.assertEqual(second.data['balance'],90)
        self.assertEqual(second.data['dayList'],self.archive['dayList'])
        self.assertTrue(self.legacy.exists())
    async def test_corrupt_legacy_archive_is_not_replaced_by_empty_history(self):
        self.legacy.write_text('{bad')
        store=self.module.AppHistoryStore(self.hass,'test')
        with self.assertRaises((ValueError,json.JSONDecodeError)): await store.async_load()
        self.assertFalse((self.root/'.storage/state_grid_info.history_test').exists())

if __name__=='__main__': unittest.main()
