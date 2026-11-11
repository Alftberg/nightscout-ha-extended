"""Read Nightscout API v1 data."""

import asyncio
from datetime import datetime, timedelta, timezone

from aiohttp import ClientError, ClientTimeout


class NightscoutError(Exception):
    """Nightscout could not be read."""


class NightscoutAuthError(NightscoutError):
    """Nightscout refused access."""


class NightscoutClient:
    def __init__(self, session, url, token=""):
        self.session = session
        self.url = url
        self.token = token

    async def _get(self, endpoint, count, **filters):
        params = {"count": count, **filters}
        if self.token:
            params["token"] = self.token
        try:
            async with self.session.get(
                f"{self.url}/api/v1/{endpoint}.json",
                params=params,
                timeout=ClientTimeout(total=15),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise NightscoutAuthError("Nightscout refused read access")
                if response.status != 200:
                    raise NightscoutError(f"Nightscout returned HTTP {response.status}")
                records = await response.json()
        except (ClientError, TimeoutError, asyncio.TimeoutError, ValueError):
            raise NightscoutError("Could not read Nightscout API response") from None

        if not isinstance(records, list) or any(
            not isinstance(record, dict) for record in records
        ):
            raise NightscoutError("Unexpected Nightscout response format")
        return records

    async def fetch(self, *, seed_history=False):
        if seed_history:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
            entries = self._get(
                "entries/sgv", 500,
                **{"find[date][$gte]": int(cutoff.timestamp() * 1000)},
            )
        else:
            entries = self._get("entries/sgv", 5)
        return await asyncio.gather(entries, self._get("devicestatus", 20))

    async def fetch_treatment_events(self, event_types):
        results = await asyncio.gather(
            *(
                self._get(
                    "treatments",
                    5,
                    **{
                        "find[eventType]": event_type,
                        "find[created_at][$gte]": "1970-01-01",
                    },
                )
                for event_type in event_types
            )
        )
        return [record for records in results for record in records]

    async def fetch_bolus_history(self):
        start = datetime.now(timezone.utc) - timedelta(hours=6)
        return await self._get("treatments", 500, **{
            "find[created_at][$gte]": start.isoformat(),
            "find[insulin][$gt]": 0,
        })

    async def fetch_profiles(self):
        return await self._get("profile", 5)


    async def fetch_basal_history(self):
        return await self._get(
            "treatments", 500,
            **{"find[eventType]": "Temp Basal", "find[created_at][$gte]": "1970-01-01"},
        )
