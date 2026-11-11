"""Serve the Nightscout dashboard strategy."""

import logging
from pathlib import Path
from urllib.parse import urlsplit

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, GRAPH_DEFAULTS, TARGET_BAND_DEFAULTS, GLUCOSE_AXIS_DEFAULTS, GLUCOSE_COLOR_DEFAULTS

_LOGGER = logging.getLogger(__name__)
URL = "/nightscout_extended/dashboard.js"


async def async_setup_dashboard(hass):
    path = Path(__file__).parent / "frontend/nightscout-dashboard.js"
    await hass.http.async_register_static_paths([StaticPathConfig(URL, str(path), False)])
    resources = hass.data[LOVELACE_DATA].resources
    if isinstance(resources, ResourceStorageCollection):
        await resources.async_get_info()
        desired_url = f"{URL}?v=0.1.29"
        matching = [
            item for item in resources.async_items()
            if item["url"].startswith("/") and urlsplit(item["url"]).path == URL
            and not urlsplit(item["url"]).netloc
        ]
        if not matching:
            await resources.async_create_item({"url": desired_url, "res_type": "module"})
        else:
            existing, *duplicates = matching
            if existing["url"] != desired_url or existing["type"] != "module":
                await resources.async_update_item(
                    existing["id"], {"url": desired_url, "res_type": "module"}
                )
            for duplicate in duplicates:
                await resources.async_delete_item(duplicate["id"])
    else:
        _LOGGER.debug("Add %s as a module in YAML-managed Lovelace resources", URL)
    websocket_api.async_register_command(hass, dashboard_entities)


@websocket_api.websocket_command({vol.Required("type"): "nightscout_extended/dashboard_entities"})
@callback
def dashboard_entities(hass, connection, msg):
    registry = er.async_get(hass)
    connection.send_result(msg["id"], [
        {
            "config_entry_id": entity.config_entry_id,
            "unique_id": entity.unique_id,
            "entity_id": entity.entity_id,
            "device_id": entity.device_id,
            "dashboard_tab_name": entry.options.get("dashboard_tab_name"),
            **({"bolus_visible": entry.options.get("graph_bolus", GRAPH_DEFAULTS["bolus"]),
                "target_band": {
                key: entry.options.get(key, default)
                for key, default in TARGET_BAND_DEFAULTS.items()
            }, "glucose_colors": {
                key: entry.options.get(key, default)
                for key, default in GLUCOSE_COLOR_DEFAULTS.items()
            }, "glucose_axis": {
                key: entry.options.get(key, default)
                for key, default in GLUCOSE_AXIS_DEFAULTS.items()
            }} if key == "glucose" else {}),
            "graph_visible": entry.options.get(f"graph_{key}", GRAPH_DEFAULTS.get(key, False)),
        }
        for entry in hass.config_entries.async_entries(DOMAIN)
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        for key in (entity.unique_id.removeprefix(f"{entry.entry_id}_"),)
        if entity.platform == DOMAIN and not entity.disabled_by and not entity.hidden_by
        and connection.user.permissions.check_entity(entity.entity_id, "read")
    ])
