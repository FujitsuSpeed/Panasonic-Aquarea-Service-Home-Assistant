"""Config flow for Panasonic Aquarea integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import AquareaAuthError, AquareaApiError, AquareaClient, AquareaConnectionError
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_DEVICE_GUID,
    CONF_DEVICE_NAME,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate_credentials(
    username: str, password: str
) -> tuple[list[dict], AquareaClient]:
    """Log in and return (devices, client).

    The caller is responsible for closing the client when it is no longer needed.
    """
    client = AquareaClient()
    try:
        await client.login(username, password)
        devices = await client.get_devices()
        return devices, client
    except Exception:
        await client.close()
        raise


class AquareaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._devices: list[dict] = []
        self._client: AquareaClient | None = None

    async def _close_client(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial credentials step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                devices, client = await _validate_credentials(username, password)
            except AquareaAuthError:
                errors["base"] = "invalid_auth"
            except AquareaConnectionError:
                errors["base"] = "cannot_connect"
            except AquareaApiError as exc:
                _LOGGER.error("Aquarea API error during login: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during Aquarea login: %s", exc)
                errors["base"] = "unknown"
            else:
                # Close previous client if user is retrying
                await self._close_client()
                self._username = username
                self._password = password
                self._devices = devices
                self._client = client

                if not devices:
                    await self._close_client()
                    return self.async_abort(reason="no_devices")

                if len(devices) == 1:
                    return await self._create_entry(devices[0])

                return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user select which device to add."""
        if user_input is not None:
            selected_guid = user_input[CONF_DEVICE_GUID]
            device = next(
                d for d in self._devices if d["deviceGuid"] == selected_guid
            )
            return await self._create_entry(device)

        device_options = {
            d["deviceGuid"]: d.get("deviceName") or d.get("name") or d["deviceGuid"]
            for d in self._devices
        }

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_GUID): vol.In(device_options)}
            ),
        )

    async def _create_entry(self, device: dict) -> FlowResult:
        """Finalise the config entry for a device."""
        await self._close_client()

        device_guid = device["deviceGuid"]
        device_name = device.get("deviceName") or device.get("name") or DEFAULT_NAME

        await self.async_set_unique_id(device_guid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=device_name,
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_GUID: device_guid,
                CONF_DEVICE_NAME: device_name,
            },
        )

    # ─── Re-auth flow ──────────────────────────────────────────────────────

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication when session has expired."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the re-auth form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(
                self.context["entry_id"]
            )
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                _, tmp_client = await _validate_credentials(username, password)
                await tmp_client.close()
            except AquareaAuthError:
                errors["base"] = "invalid_auth"
            except AquareaConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
