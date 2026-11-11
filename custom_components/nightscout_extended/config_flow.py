"""Configure Nightscout Extended through Home Assistant."""

import voluptuous as vol
from yarl import URL

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_TOKEN, CONF_UNIT_OF_MEASUREMENT, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import NightscoutAuthError, NightscoutClient, NightscoutError
from .const import DOMAIN, GLUCOSE_SENSOR_KEYS, GLUCOSE_UNITS


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
                    return self.async_create_entry(title=URL(url).host, data=data)

        fields = {}
        if not entry:
            fields[vol.Required(CONF_URL)] = str
        fields[vol.Optional(CONF_TOKEN)] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
        return self.async_show_form(step_id=step, data_schema=vol.Schema(fields), errors=errors)

class NightscoutOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        entry = self.config_entry
        registry = er.async_get(self.hass)
        entity_ids = [
            registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")
            for key in GLUCOSE_SENSOR_KEYS
        ]
        if user_input is not None:
            unit = user_input[CONF_UNIT_OF_MEASUREMENT]
            for entity_id in entity_ids:
                if entity_id is not None:
                    sensor_options = registry.async_get(entity_id).options.get("sensor", {})
                    registry.async_update_entity_options(
                        entity_id,
                        "sensor",
                        {**sensor_options, CONF_UNIT_OF_MEASUREMENT: unit},
                    )
            return self.async_create_entry(title="", data={**entry.options, **user_input})

        unit = entry.options.get(CONF_UNIT_OF_MEASUREMENT)
        if unit is None and entity_ids[0] is not None:
            state = self.hass.states.get(entity_ids[0])
            if state is not None:
                unit = state.attributes.get(CONF_UNIT_OF_MEASUREMENT)
        field = (
            vol.Required(CONF_UNIT_OF_MEASUREMENT, default=unit)
            if unit in GLUCOSE_UNITS
            else vol.Required(CONF_UNIT_OF_MEASUREMENT)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({field: vol.In(GLUCOSE_UNITS)}),
        )
