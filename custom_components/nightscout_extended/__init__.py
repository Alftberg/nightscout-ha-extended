"""Nightscout Extended integration."""

from homeassistant.const import CONF_TOKEN, CONF_URL, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import NightscoutClient
from .coordinator import NightscoutCoordinator
from .dashboard import async_setup_dashboard
from .const import DOMAIN

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.UPDATE]


async def async_setup(hass, config):
    await async_setup_dashboard(hass)
    return True


async def async_setup_entry(hass, entry):
    client = NightscoutClient(
        async_get_clientsession(hass), entry.data[CONF_URL], entry.data.get(CONF_TOKEN, "")
    )
    coordinator = NightscoutCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def async_remove_entry(hass, entry):
    await Store(hass, 1, f"{DOMAIN}.glucose_history.{entry.entry_id}").async_remove()
