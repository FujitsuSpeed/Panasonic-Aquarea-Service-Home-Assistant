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
    """Client for the Panasonic Aquarea Service Cloud API.

    Creates and owns its own aiohttp.ClientSession so that session cookies
    (JSESSIONID) are persisted between requests.  Call ``close()`` when the
    client is no longer needed.
    """

    def __init__(self) -> None:
        # unsafe=True required because the Aquarea redirect chain may set
        # cookies on IP-addressed or single-label intermediate URLs.
        self._session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        self._base_url = API_BASE_URL

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._session.close()

    # ─── Authentication ───────────────────────────────────────────────────────

    async def login(self, username: str, password: str) -> None:
        """Authenticate with the Aquarea Service Cloud."""
        url = f"{self._base_url}{API_LOGIN_PATH}"
        payload = {
            "userId": username,
            "password": password,
            "language": 0,
        }

        try:
            async with self._session.post(
                url, json=payload, headers=self._default_headers(), ssl=True
            ) as resp:
                _LOGGER.debug("Login HTTP status: %s", resp.status)

                if resp.status == 401:
                    raise AquareaAuthError("Invalid username or password")

                if resp.status not in (200, 204):
                    body = await resp.text()
                    raise AquareaApiError(
                        f"Login failed with status {resp.status}: {body[:200]}"
                    )

                # Parse body – content_type=None avoids ContentTypeError when
                # the server returns text/html or similar instead of application/json.
                try:
                    data: dict = await resp.json(content_type=None)
                except Exception:  # noqa: BLE001
                    data = {}

                _LOGGER.debug("Login response body: %s", data)

                # The Aquarea API sometimes signals auth failure in the body
                # with a non-null errorCode even on HTTP 200.
                error_code = data.get("errorCode")
                if error_code and str(error_code) not in ("", "0", "0000", "null"):
                    raise AquareaAuthError(
                        f"Login rejected by API: {error_code} – {data.get('message', '')}"
                    )

                # Cookies are stored automatically in self._session's CookieJar.
                # Log them for debugging purposes only.
                jar_cookies = list(self._session.cookie_jar)
                _LOGGER.debug("Cookies after login: %d cookie(s) in jar", len(jar_cookies))

                if not jar_cookies:
                    _LOGGER.warning(
                        "No session cookies received after login. "
                        "Subsequent requests may fail."
                    )

        except aiohttp.ClientError as exc:
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

    async def set_operation_status(self, device_guid: str, status: int) -> None:
        """Turn the device on (1) or off (0)."""
        await self._set_status(device_guid, {"operationStatus": status})

    async def set_operation_mode(self, device_guid: str, mode: int) -> None:
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

    async def set_tank_temperature(self, device_guid: str, temperature: float) -> None:
        """Set the domestic hot-water tank temperature setpoint."""
        await self._set_tank_status(device_guid, {"heatSet": temperature})

    async def set_tank_boost(self, device_guid: str, boost: int) -> None:
        """Enable (1) or disable (0) tank boost heating."""
        await self._set_tank_status(device_guid, {"boostHeat": boost})

    async def set_tank_operation_status(self, device_guid: str, status: int) -> None:
        """Turn tank heating on (1) or off (0)."""
        await self._set_tank_status(device_guid, {"operationStatus": status})

    async def set_force_heater(self, device_guid: str, force: int) -> None:
        """Enable (1) or disable (0) the auxiliary/backup heater."""
        await self._set_status(device_guid, {"forceHeater": force})

    async def set_holiday_mode(self, device_guid: str, mode: int) -> None:
        """Enable (1) or disable (0) holiday/away mode."""
        await self._set_status(device_guid, {"holidayTimer": mode})

    # ─── Internal helpers ─────────────────────────────────────────────────────

    async def _set_status(self, device_guid: str, fields: dict[str, Any]) -> None:
        path = API_DEVICE_STATUS_PATH.format(device_guid=device_guid)
        url = f"{self._base_url}{path}"
        await self._post(url, payload={"status": [{"deviceGuid": device_guid, **fields}]})

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

    async def _set_tank_status(self, device_guid: str, fields: dict[str, Any]) -> None:
        path = API_DEVICE_STATUS_PATH.format(device_guid=device_guid)
        url = f"{self._base_url}{path}"
        payload = {"status": [{"deviceGuid": device_guid, "tankStatus": [fields]}]}
        await self._post(url, payload=payload)

    async def _get(self, url: str) -> dict[str, Any]:
        try:
            async with self._session.get(
                url, headers=self._default_headers(), ssl=True
            ) as resp:
                await self._check_response(resp)
                return await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise AquareaConnectionError(str(exc)) from exc

    async def _post(self, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        try:
            async with self._session.post(
                url,
                json=payload,
                headers=self._default_headers(),
                ssl=True,
            ) as resp:
                await self._check_response(resp)
                if resp.status == 204:
                    return {}
                return await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise AquareaConnectionError(str(exc)) from exc

    async def _check_response(self, resp: aiohttp.ClientResponse) -> None:
        if resp.status == 401:
            raise AquareaAuthError("Session expired – please re-authenticate")
        if resp.status not in (200, 204):
            body = await resp.text()
            raise AquareaApiError(
                f"API error {resp.status} for {resp.url}: {body[:200]}"
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
