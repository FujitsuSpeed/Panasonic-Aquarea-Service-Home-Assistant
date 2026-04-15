"""DataUpdateCoordinator for Panasonic Aquarea."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AquareaAuthError, AquareaApiError, AquareaClient, AquareaConnectionError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AquareaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch data from the Aquarea Service Cloud on a fixed interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AquareaClient,
        device_guid: str,
        device_name: str,
    ) -> None:
        self.client = client
        self.device_guid = device_guid
        self.device_name = device_name

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {device_name}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest device status."""
        try:
            status = await self.client.get_device_status(self.device_guid)
        except AquareaAuthError as exc:
            # Trigger a re-auth flow in Home Assistant
            raise ConfigEntryAuthFailed(exc) from exc
        except (AquareaApiError, AquareaConnectionError) as exc:
            raise UpdateFailed(f"Error fetching Aquarea data: {exc}") from exc

        _LOGGER.debug("Device status for %s: %s", self.device_guid, status)
        return status
