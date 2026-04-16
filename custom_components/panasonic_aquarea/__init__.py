"""Panasonic Aquarea Service Cloud integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import AquareaAuthError, AquareaClient, AquareaConnectionError
from .const import (
    CONF_DEVICE_GUID,
    CONF_DEVICE_NAME,
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AquareaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

_CLIENT_KEY = "client"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Aquarea from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    device_guid: str = entry.data[CONF_DEVICE_GUID]
    device_name: str = entry.data.get(CONF_DEVICE_NAME, device_guid)

    # AquareaClient creates its own aiohttp session with a proper CookieJar.
    client = AquareaClient()

    try:
        await client.login(username, password)
    except AquareaAuthError as exc:
        await client.close()
        raise ConfigEntryAuthFailed(exc) from exc
    except AquareaConnectionError as exc:
        await client.close()
        raise ConfigEntryNotReady(exc) from exc

    coordinator = AquareaDataUpdateCoordinator(
        hass, client, device_guid, device_name
    )

    # Fetch initial data – raises ConfigEntryNotReady on failure.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
        _CLIENT_KEY: client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the HTTP session."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data[_CLIENT_KEY].close()
    return unload_ok
