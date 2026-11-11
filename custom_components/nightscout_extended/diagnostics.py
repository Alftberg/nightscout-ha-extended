"""Expose connection health without credentials or telemetry."""


async def async_get_config_entry_diagnostics(hass, entry):
    return {"last_update_success": entry.runtime_data.last_update_success}
