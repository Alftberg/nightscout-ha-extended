"""Monitor LoopWorkspace releases in Home Assistant."""

from datetime import timedelta
import logging

from aiohttp import ClientError, ClientTimeout
from homeassistant.components import persistent_notification
from homeassistant.components.update import UpdateEntity, UpdateEntityDescription
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .entity import NightscoutEntity
from .releases import RELEASES_URL, release_version

API_URL = "https://api.github.com/repos/LoopKit/LoopWorkspace/releases/latest"
DESCRIPTION = UpdateEntityDescription(key="loop_update", translation_key="loop_update")


async def async_setup_entry(hass, entry, async_add_entities):
    releases = LoopReleases(hass, entry)
    async_add_entities([LoopUpdate(entry, releases)])


class LoopReleases(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            config_entry=entry,
            name="LoopWorkspace releases",
            update_interval=timedelta(hours=6),
            always_update=False,
        )

    @property
    def uses_loop(self):
        source = self.config_entry.runtime_data
        return source.last_update_success and release_version(
            (source.data or {}).get("loop_version")
        ) is not None

    async def _async_update_data(self):
        if not self.uses_loop:
            return None
        try:
            async with async_get_clientsession(self.hass).get(
                API_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=ClientTimeout(total=15),
                allow_redirects=False,
            ) as response:
                response.raise_for_status()
                release = await response.json()
        except (ClientError, TimeoutError, ValueError) as error:
            raise UpdateFailed("Could not read the latest LoopWorkspace release") from error

        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            raise UpdateFailed("Unexpected LoopWorkspace release response")
        tag = release.get("tag_name")
        if release_version(tag) is None:
            raise UpdateFailed("Unrecognized LoopWorkspace release tag")
        return tag


class LoopUpdate(NightscoutEntity, UpdateEntity):
    _attr_title = "Loop"

    def __init__(self, entry, releases):
        super().__init__(entry, DESCRIPTION)
        self.releases = releases
        self.notification_id = f"nightscout_loop_update_{entry.entry_id}"
        self.store = Store(releases.hass, 1, self.notification_id)
        self.last_notified = None

    async def async_added_to_hass(self):
        self.last_notified = await self.store.async_load()
        await super().async_added_to_hass()
        self.async_on_remove(self.releases.async_add_listener(self._handle_coordinator_update))
        self._using_loop = self.releases.uses_loop
        self.async_on_remove(self.coordinator.async_add_listener(self._check_loop_usage))
        if self._using_loop:
            self._refresh_loop_release()

    @callback
    def _refresh_loop_release(self):
        task = self.hass.async_create_task(self.releases.async_request_refresh())
        self.async_on_remove(task.cancel)

    @callback
    def _check_loop_usage(self):
        uses_loop = self.releases.uses_loop
        if uses_loop and not self._using_loop:
            self._refresh_loop_release()
        self._using_loop = uses_loop

    @property
    def available(self):
        return (
            super().available
            and self.releases.last_update_success
            and self.latest_version is not None
            and self.installed_version is not None
        )

    @property
    def installed_version(self):
        version = release_version(self.coordinator.data.get("loop_version"))
        return ".".join(map(str, version)) if version is not None else None

    @property
    def latest_version(self):
        return self.releases.data

    @property
    def release_url(self):
        return f"{RELEASES_URL}/tag/{self.latest_version}" if self.latest_version else RELEASES_URL

    def version_is_newer(self, latest_version, installed_version):
        latest = release_version(latest_version)
        installed = release_version(installed_version)
        return latest is not None and installed is not None and latest > installed

    @callback
    def _handle_coordinator_update(self):
        if self.available:
            latest = self.latest_version
            if self.version_is_newer(latest, self.installed_version):
                if latest != self.last_notified:
                    self.last_notified = latest
                    persistent_notification.async_create(
                        self.hass,
                        f"Loop {latest} is available. Installed version: "
                        f"{self.installed_version}. [Release notes]({self.release_url})",
                        title="Loop update available",
                        notification_id=self.notification_id,
                    )
                    self.store.async_delay_save(lambda: self.last_notified, 1)
            else:
                persistent_notification.async_dismiss(self.hass, self.notification_id)
        super()._handle_coordinator_update()
