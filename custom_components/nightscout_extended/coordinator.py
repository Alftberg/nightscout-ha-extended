"""Poll Nightscout once for all entities."""

import asyncio
from datetime import datetime, timedelta, timezone
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NightscoutAuthError, NightscoutError
from .const import AGE_EVENTS, DOMAIN, OVERRIDE_EVENTS
from .data import active_override_profile, event_age_hours, parse


class NightscoutCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self):
        try:
            entries, statuses = await self.client.fetch()
        except NightscoutAuthError as error:
            raise ConfigEntryAuthFailed(str(error)) from error
        except NightscoutError as error:
            raise UpdateFailed(str(error)) from error
        data = parse(entries, statuses, datetime.now(timezone.utc))
        event_groups = list(AGE_EVENTS.values())
        fetch_override = data.get("override_active") is True
        if fetch_override:
            event_groups.append(OVERRIDE_EVENTS)
        ages = await asyncio.gather(
            *(self._async_fetch_events(types) for types in event_groups)
        )
        now = datetime.now(timezone.utc)
        data = parse(entries, statuses, now)
        override_events = ages.pop() if fetch_override else []
        if data.get("override_active") is True:
            name, attributes = active_override_profile(override_events, now)
            data["override_profile"] = name
            data["override_attributes"].update(attributes)
        for (key, event_types), records in zip(AGE_EVENTS.items(), ages, strict=True):
            data[key] = event_age_hours(records, event_types, now)
        return data

    async def _async_fetch_events(self, event_types):
        try:
            return await self.client.fetch_treatment_events(event_types)
        except NightscoutError as error:
            self.logger.debug("Could not read Nightscout treatment events: %s", error)
            return []
