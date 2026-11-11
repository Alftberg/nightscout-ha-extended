"""Poll Nightscout once for all entities."""

import asyncio
from datetime import datetime, timedelta, timezone
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NightscoutAuthError, NightscoutError
from .const import AGE_EVENTS, DOMAIN, OVERRIDE_EVENTS
from .data import active_override_profile, basal_history, bolus_history, combined_basal_history, event_age_hours, glucose_history, merge_glucose_history, parse, saved_profile, treatment_snapshot


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
        self.history_store = Store(hass, 1, f"{DOMAIN}.glucose_history.{entry.entry_id}")
        self.history = None

    async def _async_setup(self):
        self.history = await self.history_store.async_load()

    async def _async_update_data(self):
        try:
            entries, statuses = await self.client.fetch(seed_history=self.history is None)
        except NightscoutAuthError as error:
            raise ConfigEntryAuthFailed(str(error)) from error
        except NightscoutError as error:
            raise UpdateFailed(str(error)) from error
        data = parse(entries, statuses, datetime.now(timezone.utc))
        event_groups = list(AGE_EVENTS.values())
        fetch_override = data.get("override_active") is True
        if fetch_override:
            event_groups.append(OVERRIDE_EVENTS)
        ages, treatments, profiles, basal_records, bolus_records = await asyncio.gather(
            asyncio.gather(*(self._async_fetch_events(types) for types in event_groups)),
            asyncio.gather(*(
                self._async_fetch_events((kind,))
                for kind in ("Carb Correction", "Correction Bolus")
            )),
            self._async_fetch_profiles(),
            self._async_fetch_basal_history(),
            self._async_fetch_bolus_history(),
        )
        now = datetime.now(timezone.utc)
        data = parse(entries, statuses, now)
        override_events = ages.pop() if fetch_override else []
        if data.get("override_active") is True:
            name, attributes = active_override_profile(override_events, now)
            if name is not None and "override_profile" not in data:
                data["override_profile"] = name
            if name is None or data.get("override_profile") == name:
                data["override_attributes"].update(attributes)
        for (key, event_types), records in zip(AGE_EVENTS.items(), ages, strict=True):
            data[key] = event_age_hours(records, event_types, now)
        data.update(treatment_snapshot((basal_records or []) + [record for group in treatments for record in group], now))
        data["bolus_history"] = bolus_history(bolus_records, now)
        data["basal_history"] = basal_history(basal_records or [], now)
        data["combined_basal_history"] = (
            combined_basal_history(data["basal_history"], profiles, now)
            if basal_records is not None else []
        )
        history = merge_glucose_history(self.history or [], glucose_history(entries, now), now)
        if history != self.history:
            await self.history_store.async_save(history)
        self.history = history
        data["glucose_history"] = history
        data.update(saved_profile(profiles, now))
        return data

    async def _async_fetch_events(self, event_types):
        try:
            return await self.client.fetch_treatment_events(event_types)
        except NightscoutError as error:
            self.logger.debug("Could not read Nightscout treatment events: %s", error)
            return []

    async def _async_fetch_profiles(self):
        try:
            return await self.client.fetch_profiles()
        except NightscoutError as error:
            self.logger.debug("Could not read Nightscout profiles: %s", error)
            return []

    async def _async_fetch_basal_history(self):
        try:
            return await self.client.fetch_basal_history()
        except NightscoutError as error:
            self.logger.debug("Could not read Nightscout basal history: %s", error)
            return None

    async def _async_fetch_bolus_history(self):
        try:
            return await self.client.fetch_bolus_history()
        except NightscoutError as error:
            self.logger.debug("Could not read Nightscout bolus history: %s", error)
            return []
