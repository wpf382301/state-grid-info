"""Durable billing archive with one-time import of the original JSON history."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

from homeassistant.helpers.storage import Store


class AppHistoryStore:
    def __init__(self, hass, consumer_number):
        self.hass = hass
        self._store = Store(hass, 1, f'state_grid_info.history_{consumer_number}')
        self._legacy = Path(hass.config.path(f'state_grid_info_{consumer_number}.json'))
        self._data = {}
        self._lock = asyncio.Lock()

    @property
    def data(self):
        return deepcopy(self._data)

    def _read_legacy(self):
        if not self._legacy.exists():
            return {}
        data = json.loads(self._legacy.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or any(not isinstance(data.get(k,[]),list) for k in ('dayList','monthList','yearList')):
            raise ValueError('Invalid legacy State Grid history; keep the original file for recovery')
        return data

    async def async_load(self):
        data = await self._store.async_load()
        if data is None:
            data = await self.hass.async_add_executor_job(self._read_legacy)
            if data:
                await self._store.async_save(data)
        self._data = data or {}

    async def async_save(self, data):
        async with self._lock:
            if data != self._data:
                await self._store.async_save(data)
                self._data = deepcopy(data)
        return self.data
