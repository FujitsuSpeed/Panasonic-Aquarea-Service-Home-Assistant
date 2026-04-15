"""Panasonic Aquarea Service Cloud integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AquareaAuthError, AquareaClient, AquareaConnectionError
from .const import (
    CONF_DEVICE_GUID,
    CONF_DEVICE_NAME,
    COORDINATOR,
    DEVICE_INFO,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AquareaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Aquarea from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    device_guid: str = entry.data[CONF_DEVICE_GUID]
    device_name: str = entry.data.get(CONF_DEVICE_NAME, device_guid)

    session = async_get_clientsession(hass)
    client = AquareaClient(session)

    try:
        await client.login(username, password)
    except AquareaAuthError as exc:
        raise ConfigEntryAuthFailed(exc) from exc
    except AquareaConnectionError as exc:
        raise ConfigEntryNotReady(exc) from exc

    coordinator = AquareaDataUpdateCoordinator(
        hass, client, device_guid, device_name
    )

    # Fetch initial data – raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
