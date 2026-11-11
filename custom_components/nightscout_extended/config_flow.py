"""Configure Nightscout Extended through Home Assistant."""

from math import isfinite
import re

import voluptuous as vol
from yarl import URL

from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.const import CONF_TOKEN, CONF_UNIT_OF_MEASUREMENT, CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode, TextSelector, TextSelectorConfig, TextSelectorType

from .api import NightscoutAuthError, NightscoutClient, NightscoutError
from .const import DOMAIN, GLUCOSE_SENSOR_KEYS, GLUCOSE_UNITS, GRAPH_DEFAULTS, TARGET_BAND_DEFAULTS, GLUCOSE_AXIS_DEFAULTS, GLUCOSE_COLOR_DEFAULTS


def normalize_url(value):
    url = URL(value.strip())
    if (
        url.scheme not in ("http", "https")
        or not url.host
        or url.user is not None
        or url.query_string
        or url.fragment
    ):
        raise ValueError("Expected a Nightscout base URL")
    return str(url).rstrip("/")


class NightscoutConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NightscoutOptionsFlow()

    async def async_step_user(self, user_input=None):
        return await self._async_configure("user", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._async_configure("reauth_confirm", user_input)

    async def _async_configure(self, step, user_input):
        errors = {}
        entry = self._get_reauth_entry() if step == "reauth_confirm" else None
        if user_input is not None:
            try:
                url = entry.data[CONF_URL] if entry else normalize_url(user_input[CONF_URL])
            except ValueError:
                errors[CONF_URL] = "invalid_url"
            else:
                if not entry:
                    await self.async_set_unique_id(url)
                    self._abort_if_unique_id_configured()
                token = user_input.get(CONF_TOKEN, "").strip()
                client = NightscoutClient(async_get_clientsession(self.hass), url, token)
                try:
                    await client.fetch()
                except NightscoutAuthError:
                    errors["base"] = "invalid_auth"
                except NightscoutError:
                    errors["base"] = "cannot_connect"
                else:
                    data = {CONF_URL: url, CONF_TOKEN: token}
                    if entry:
                        return self.async_update_reload_and_abort(entry, data=data)
                    return self.async_create_entry(
                        title=URL(url).host, data=data,
                        options={CONF_UNIT_OF_MEASUREMENT: "mmol/L"},
                    )

        fields = {}
        if not entry:
            fields[vol.Required(CONF_URL)] = str
        fields[vol.Optional(CONF_TOKEN)] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
        return self.async_show_form(step_id=step, data_schema=vol.Schema(fields), errors=errors)

class NightscoutOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        entry = self.config_entry
        registry = er.async_get(self.hass)
        entity_ids = [
            registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")
            for key in GLUCOSE_SENSOR_KEYS
        ]
        errors = {}
        values = entry.options if user_input is None else user_input
        if user_input is not None:
            user_input = {
                **user_input, **user_input["band_settings"], **user_input["axis_settings"],
                **user_input["glucose_colors"],
            }
            values = user_input
            if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", user_input[key]) for key in GLUCOSE_COLOR_DEFAULTS):
                errors["base"] = "invalid_glucose_color"
            low, high = user_input["target_low"], user_input["target_high"]
            if not (isfinite(high) and 0 < low < high):
                errors["base"] = "invalid_target_range"
            low, high = user_input["axis_low"], user_input["axis_high"]
            if not (low.is_integer() and high.is_integer() and 0 <= low < high):
                errors["base"] = "invalid_axis_range"
        if user_input is not None and not errors:
            unit = user_input[CONF_UNIT_OF_MEASUREMENT]
            for entity_id in entity_ids:
                if entity_id is not None:
                    sensor_options = registry.async_get(entity_id).options.get("sensor", {})
                    registry.async_update_entity_options(
                        entity_id,
                        "sensor",
                        {**sensor_options, CONF_UNIT_OF_MEASUREMENT: unit},
                    )
            selected = user_input["graph_series"]
            options = {**entry.options, CONF_UNIT_OF_MEASUREMENT: unit}
            options["dashboard_tab_name"] = user_input.get("dashboard_tab_name", "").strip()
            options.update({key: user_input[key] for key in TARGET_BAND_DEFAULTS})
            options.update({key: user_input[key] for key in GLUCOSE_COLOR_DEFAULTS})
            options.update({key: int(user_input[key]) for key in GLUCOSE_AXIS_DEFAULTS})
            options.update({f"graph_{key}": key in selected for key in GRAPH_DEFAULTS})
            return self.async_create_entry(title="", data=options)

        unit = values.get(CONF_UNIT_OF_MEASUREMENT)
        if unit is None and entity_ids[0] is not None:
            state = self.hass.states.get(entity_ids[0])
            if state is not None:
                unit = state.attributes.get(CONF_UNIT_OF_MEASUREMENT)
        field = (
            vol.Required(CONF_UNIT_OF_MEASUREMENT, default=unit)
            if unit in GLUCOSE_UNITS
            else vol.Required(CONF_UNIT_OF_MEASUREMENT, default="mmol/L")
        )
        selected = values.get("graph_series", [
            key for key, default in GRAPH_DEFAULTS.items()
            if entry.options.get(f"graph_{key}", default)
        ])
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema({
                vol.Optional("dashboard_tab_name", default=values.get("dashboard_tab_name", "")): str,
                field: SelectSelector(SelectSelectorConfig(
                    options=list(GLUCOSE_UNITS),
                    mode=SelectSelectorMode.DROPDOWN,
                )),
                vol.Required("graph_series", default=selected): SelectSelector(SelectSelectorConfig(
                    options=list(GRAPH_DEFAULTS),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key="graph_series",
                )),
                vol.Required("band_settings"): section(vol.Schema({
                    vol.Required(key, default=values.get(key, default)): (
                        bool if key == "target_band" else vol.Coerce(float)
                    )
                    for key, default in TARGET_BAND_DEFAULTS.items()
                })),
                vol.Required("glucose_colors"): section(vol.Schema({
                    vol.Required(key, default=values.get(key, default)): str
                    for key, default in GLUCOSE_COLOR_DEFAULTS.items()
                })),
                vol.Required("axis_settings"): section(vol.Schema({
                    vol.Required(key, default=values.get(key, default)): vol.Coerce(float)
                    for key, default in GLUCOSE_AXIS_DEFAULTS.items()
                })),
            }),
        )
