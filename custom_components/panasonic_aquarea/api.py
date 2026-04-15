"""Panasonic Aquarea Service Cloud API client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_LOGIN_PATH,
    API_DEVICES_PATH,
    API_DEVICE_STATUS_PATH,
    API_USER_AGENT,
    API_APP_TYPE,
)

_LOGGER = logging.getLogger(__name__)


class AquareaAuthError(Exception):
    """Raised when authentication fails."""


class AquareaApiError(Exception):
    """Raised when an API call fails."""


class AquareaConnectionError(Exception):
    """Raised when the connection to the API fails."""


class AquareaClient:
    """Client for the Panasonic Aquarea Service Cloud API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._cookies: dict[str, str] = {}
        self._base_url = API_BASE_URL

    # ─── Authentication ───────────────────────────────────────────────────────

    async def login(self, username: str, password: str) -> None:
        """Authenticate with the Aquarea Service Cloud."""
        url = f"{self._base_url}{API_LOGIN_PATH}"
        payload = {
            "userId": username,
            "password": password,
            "language": 0,
        }
        headers = self._default_headers()

        try:
            async with self._session.post(
                url, json=payload, headers=headers, ssl=True
            ) as resp:
                if resp.status == 401:
                    raise AquareaAuthError("Invalid username or password")
                if resp.status != 200:
                    body = await resp.text()
                    raise AquareaApiError(
                        f"Login failed with status {resp.status}: {body}"
                    )

                data = await resp.json()
                _LOGGER.debug("Login response: %s", data)

                # Store session cookies
                self._cookies = {
                    key: morsel.value
                    for key, morsel in resp.cookies.items()
                }

                if not self._cookies:
                    # Some API versions return token in body
                    token = data.get("token") or data.get("sessionToken")
                    if token:
                        self._cookies["JSESSIONID"] = token
                    else:
                        raise AquareaAuthError(
                            "Login succeeded but no session cookie received"
                        )

        except aiohttp.ClientConnectorError as exc:
            raise AquareaConnectionError(
                f"Cannot connect to Aquarea Service: {exc}"
            ) from exc

    # ─── Devices ──────────────────────────────────────────────────────────────

    async def get_devices(self) -> list[dict[str, Any]]:
        """Return a list of registered devices."""
        url = f"{self._base_url}{API_DEVICES_PATH}"
        data = await self._get(url)

        devices: list[dict[str, Any]] = data.get("device", [])
        _LOGGER.debug("Found %d device(s)", len(devices))
        return devices

    # ─── Device Status ────────────────────────────────────────────────────────

    async def get_device_status(self, device_guid: str) -> dict[str, Any]:
        """Return the current status of a device."""
        path = API_DEVICE_STATUS_PATH.format(device_guid=device_guid)
        url = f"{self._base_url}{path}"
        data = await self._post(url, payload=None)

        status_list: list[dict] = data.get("status", [])
        if not status_list:
            raise AquareaApiError(
                f"No status returned for device {device_guid}"
            )
        return status_list[0]

    # ─── Control methods ──────────────────────────────────────────────────────

    async def set_operation_status(
        self, device_guid: str, status: int
    ) -> None:
        """Turn the device on (1) or off (0)."""
        await self._set_status(device_guid, {"operationStatus": status})

    async def set_operation_mode(
        self, device_guid: str, mode: int
    ) -> None:
        """Set the operation mode (heat / cool / auto / dhw …)."""
        await self._set_status(device_guid, {"operationMode": mode})

    async def set_zone_heat_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        """Set the heating water temperature setpoint for a zone."""
        await self._set_zone_status(
            device_guid, zone_id, {"heatTemperature": temperature}
        )

    async def set_zone_cool_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        """Set the cooling water temperature setpoint for a zone."""
        await self._set_zone_status(
            device_guid, zone_id, {"coolTemperature": temperature}
        )

    async def set_zone_room_heat_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        """Set the room heating setpoint for a zone."""
        await self._set_zone_status(
            device_guid, zone_id, {"heatRoomSetTemp": temperature}
        )

    async def set_zone_room_cool_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        """Set the room cooling setpoint for a zone."""
        await self._set_zone_status(
            device_guid, zone_id, {"coolRoomSetTemp": temperature}
        )

    async def set_tank_temperature(
        self, device_guid: str, temperature: float
    ) -> None:
        """Set the domestic hot-water tank temperature setpoint."""
        await self._set_tank_status(device_guid, {"heatSet": temperature})

    async def set_tank_boost(
        self, device_guid: str, boost: int
    ) -> None:
        """Enable (1) or disable (0) tank boost heating."""
        await self._set_tank_status(device_guid, {"boostHeat": boost})

    async def set_tank_operation_status(
        self, device_guid: str, status: int
    ) -> None:
        """Turn tank heating on (1) or off (0)."""
        await self._set_tank_status(device_guid, {"operationStatus": status})

    async def set_force_heater(
        self, device_guid: str, force: int
    ) -> None:
        """Enable (1) or disable (0) the auxiliary/backup heater."""
        await self._set_status(device_guid, {"forceHeater": force})

    async def set_holiday_mode(
        self, device_guid: str, mode: int
    ) -> None:
        """Enable (1) or disable (0) holiday/away mode."""
        await self._set_status(device_guid, {"holidayTimer": mode})

    # ─── Internal helpers ─────────────────────────────────────────────────────

    async def _set_status(
        self, device_guid: str, fields: dict[str, Any]
    ) -> None:
        path = API_DEVICE_STATUS_PATH.format(device_guid=device_guid)
        url = f"{self._base_url}{path}"
        payload = {"status": [{"deviceGuid": device_guid, **fields}]}
        await self._post(url, payload=payload)

    async def _set_zone_status(
        self, device_guid: str, zone_id: int, fields: dict[str, Any]
    ) -> None:
        path = API_DEVICE_STATUS_PATH.format(device_guid=device_guid)
        url = f"{self._base_url}{path}"
        payload = {
            "status": [
                {
                    "deviceGuid": device_guid,
                    "zoneStatus": [{"zoneId": zone_id, **fields}],
                }
            ]
        }
        await self._post(url, payload=payload)

    async def _set_tank_status(
        self, device_guid: str, fields: dict[str, Any]
    ) -> None:
        path = API_DEVICE_STATUS_PATH.format(device_guid=device_guid)
        url = f"{self._base_url}{path}"
        payload = {
            "status": [
                {
                    "deviceGuid": device_guid,
                    "tankStatus": [fields],
                }
            ]
        }
        await self._post(url, payload=payload)

    async def _get(self, url: str) -> dict[str, Any]:
        try:
            async with self._session.get(
                url, headers=self._default_headers(), cookies=self._cookies, ssl=True
            ) as resp:
                await self._handle_response_errors(resp)
                return await resp.json()
        except aiohttp.ClientConnectorError as exc:
            raise AquareaConnectionError(str(exc)) from exc

    async def _post(
        self, url: str, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        try:
            async with self._session.post(
                url,
                json=payload,
                headers=self._default_headers(),
                cookies=self._cookies,
                ssl=True,
            ) as resp:
                await self._handle_response_errors(resp)
                return await resp.json()
        except aiohttp.ClientConnectorError as exc:
            raise AquareaConnectionError(str(exc)) from exc

    async def _handle_response_errors(self, resp: aiohttp.ClientResponse) -> None:
        if resp.status == 401:
            raise AquareaAuthError("Session expired – please re-authenticate")
        if resp.status not in (200, 204):
            body = await resp.text()
            raise AquareaApiError(
                f"API error {resp.status} for {resp.url}: {body}"
            )

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": API_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "X-APP-TYPE": API_APP_TYPE,
            "Referer": f"{API_BASE_URL}/",
            "Origin": API_BASE_URL,
        }
