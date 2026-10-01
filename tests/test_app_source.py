"""Entity contracts exercised against a real HA state machine, no network."""
import importlib,sys,types
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import tempfile,unittest
try:
    from homeassistant.core import HomeAssistant
except ImportError:
    HomeAssistant=None

@unittest.skipIf(HomeAssistant is None,'Home Assistant runtime required')
class SourceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        root=Path(__file__).parents[1]/'custom_components/state_grid_info'
        pkg=types.ModuleType('test_grid_info');pkg.__path__=[str(root)];sys.modules['test_grid_info']=pkg
        self.source=importlib.import_module('test_grid_info.app_source')
        self.temp=tempfile.TemporaryDirectory();self.hass=HomeAssistant(self.temp.name)
        devices={'first':NS(id='first',serial_number='12349870',identifiers={('state_grid','a')},name='first'),
                 'other':NS(id='other',serial_number='56789870',identifiers={('state_grid','b')},name='other')}
        entities={str(i):NS(device_id=device,platform='state_grid',disabled_by=None,unique_id=unique,entity_id=eid)
            for i,(device,unique,eid) in enumerate([('first','a_latest_daily_usage','sensor.first'),('other','b_latest_daily_usage','sensor.other')])}
        self.p1=patch.object(self.source.dr,'async_get',return_value=NS(devices=devices));self.p1.start()
        self.p2=patch.object(self.source.er,'async_get',return_value=NS(entities=entities));self.p2.start()
    async def asyncTearDown(self):
        self.p1.stop();self.p2.stop();await self.hass.async_stop();self.temp.cleanup()
    async def test_full_household_number_prevents_suffix_collision(self):
        self.hass.states.async_set('sensor.first',4,{'daily_history':[{'day':'2026-09-30','usage':4}]})
        self.hass.states.async_set('sensor.other',99,{'daily_history':[{'day':'2026-09-30','usage':99}]})
        self.assertEqual(self.source.read_app_snapshot(self.hass,'12349870')['daily_history'][0]['usage'],4)
        self.assertIsNone(self.source.read_app_snapshot(self.hass,'9870'))
    async def test_unavailable_source_does_not_relabel_cached_attributes_as_fresh(self):
        self.hass.states.async_set('sensor.first','unavailable',{'daily_history':[{'day':'2026-09-30','usage':4}]})
        self.assertIsNone(self.source.read_app_snapshot(self.hass,'12349870'))

if __name__=='__main__':unittest.main()
