"""国家电网辅助信息集成。"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up State Grid Info from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": {**entry.data, **entry.options},
        "entities": [],
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a State Grid Info config entry."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    if coordinator is not None:
        await coordinator.async_unload()

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
