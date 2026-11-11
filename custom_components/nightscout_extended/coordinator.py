"""Poll Nightscout once for all entities."""

from datetime import datetime, timedelta, timezone
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NightscoutAuthError, NightscoutError
from .const import DOMAIN
from .data import parse


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
        return parse(entries, statuses, datetime.now(timezone.utc))
