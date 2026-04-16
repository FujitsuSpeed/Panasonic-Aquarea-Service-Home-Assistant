"""Panasonic Aquarea Service Cloud API client.

Authentication uses a multi-step OAuth2 PKCE flow via Auth0
(authglb.digital.panasonic.com).  After obtaining tokens the actual
device API is reached through accsmart.panasonic.com.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from .const import (
    API_ACC_LOGIN_PATH,
    API_APP_TYPE,
    API_APP_VERSION,
    API_BASE_URL,
    API_DEVICE_CONTROL_APINAME,
    API_DEVICE_STATUS_APINAME,
    API_DEVICES_PATH,
    API_TRANSFER_PATH,
    API_USER_AGENT,
    APP_CLIENT_ID,
    APP_REDIRECT_URI,
    AUTH0_CLIENT_B64,
    AUTH_BASE_URL,
    AUTH_CALLBACK_PATH,
    AUTH_LOGIN_PATH,
    AUTH_TOKEN_PATH,
    AUTH_USER_AGENT,
    OAUTH_AUDIENCE,
    OAUTH_SCOPE,
    OAUTH_TENANT,
)

_LOGGER = logging.getLogger(__name__)


# ─── Exceptions ───────────────────────────────────────────────────────────────

class AquareaAuthError(Exception):
    """Raised when authentication fails."""


class AquareaApiError(Exception):
    """Raised when an API call fails."""


class AquareaConnectionError(Exception):
    """Raised when the connection to the API fails."""


# ─── HTML form parser ─────────────────────────────────────────────────────────

class _HiddenFormParser(HTMLParser):
    """Extract hidden <input> fields from an HTML form."""

    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "input":
            d = dict(attrs)
            if d.get("type") == "hidden" and d.get("name"):
                self.fields[d["name"]] = d.get("value", "")


# ─── PKCE helpers ─────────────────────────────────────────────────────────────

def _pkce_verifier() -> str:
    """Generate a random PKCE code verifier (base64url, 43 chars)."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()


def _pkce_challenge(verifier: str) -> str:
    """Compute the PKCE code challenge (S256)."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


# ─── Main client ──────────────────────────────────────────────────────────────

class AquareaClient:
    """Async client for the Panasonic Aquarea Service Cloud.

    Creates and owns its own aiohttp.ClientSession; call ``close()`` when done.
    """

    def __init__(self) -> None:
        self._session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._client_id: str | None = None  # Panasonic-internal client identifier

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._session.close()

    # ─── Public: Authentication ───────────────────────────────────────────────

    async def login(self, username: str, password: str) -> None:
        """Authenticate via OAuth2 PKCE and store the resulting tokens."""
        try:
            verifier = _pkce_verifier()
            challenge = _pkce_challenge(verifier)
            state = secrets.token_urlsafe(32)

            _LOGGER.debug("OAuth step 1: authorize (PKCE)")
            csrf = await self._oauth_authorize(challenge, state)

            _LOGGER.debug("OAuth step 2: submit credentials")
            form_fields = await self._oauth_credentials(
                username, password, csrf, state, challenge
            )

            _LOGGER.debug("OAuth step 3: follow callback chain")
            auth_code = await self._oauth_callback(form_fields)

            _LOGGER.debug("OAuth step 4: exchange code for token")
            tokens = await self._oauth_token(auth_code, verifier)
            self._access_token = tokens["access_token"]
            self._refresh_token = tokens.get("refresh_token")

            _LOGGER.debug("OAuth step 5: get Panasonic client ID")
            self._client_id = await self._get_acc_client_id()
            _LOGGER.info("Aquarea login successful; client_id=%s", self._client_id)

        except (AquareaAuthError, AquareaConnectionError):
            raise
        except aiohttp.ClientError as exc:
            raise AquareaConnectionError(f"Network error during login: {exc}") from exc

    # ─── Public: Devices ──────────────────────────────────────────────────────

    async def get_devices(self) -> list[dict[str, Any]]:
        """Return Aquarea devices (deviceType == '2') from the account."""
        url = f"{API_BASE_URL}{API_DEVICES_PATH}"
        data = await self._api_get(url)

        devices: list[dict[str, Any]] = []
        for group in data.get("groupList", []):
            for dev in group.get("deviceList", group.get("deviceIdList", [])):
                # deviceType "2" = Aquarea (Air-to-Water heat pump)
                if str(dev.get("deviceType", "")) == "2":
                    devices.append(dev)

        _LOGGER.debug("Found %d Aquarea device(s)", len(devices))
        return devices

    # ─── Public: Device Status ────────────────────────────────────────────────

    async def get_device_status(self, device_guid: str) -> dict[str, Any]:
        """Return the current status of a device, trying live data first."""
        for direct in (1, 0):
            api_name = API_DEVICE_STATUS_APINAME.format(
                device_guid=device_guid, direct=direct
            )
            try:
                result = await self._transfer("GET", api_name)
                status = result.get("status") or result
                if status:
                    return status
            except AquareaApiError as exc:
                if direct == 0:
                    raise
                _LOGGER.debug(
                    "Live device status failed (%s), falling back to cached", exc
                )
        raise AquareaApiError(f"No status data for device {device_guid}")

    # ─── Public: Control ─────────────────────────────────────────────────────

    async def set_operation_status(self, device_guid: str, status: int) -> None:
        await self._control(device_guid, {"operationStatus": status})

    async def set_operation_mode(self, device_guid: str, mode: int) -> None:
        await self._control(device_guid, {"operationMode": mode})

    async def set_zone_heat_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        await self._zone_control(device_guid, zone_id, {"heatTemperature": temperature})

    async def set_zone_cool_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        await self._zone_control(device_guid, zone_id, {"coolTemperature": temperature})

    async def set_zone_room_heat_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        await self._zone_control(device_guid, zone_id, {"heatRoomSetTemp": temperature})

    async def set_zone_room_cool_temperature(
        self, device_guid: str, zone_id: int, temperature: float
    ) -> None:
        await self._zone_control(device_guid, zone_id, {"coolRoomSetTemp": temperature})

    async def set_tank_temperature(self, device_guid: str, temperature: float) -> None:
        await self._tank_control(device_guid, {"heatSet": temperature})

    async def set_tank_boost(self, device_guid: str, boost: int) -> None:
        await self._tank_control(device_guid, {"boostHeat": boost})

    async def set_tank_operation_status(self, device_guid: str, status: int) -> None:
        await self._tank_control(device_guid, {"operationStatus": status})

    async def set_force_heater(self, device_guid: str, force: int) -> None:
        await self._control(device_guid, {"forceHeater": force})

    async def set_holiday_mode(self, device_guid: str, mode: int) -> None:
        await self._control(device_guid, {"holidayTimer": mode})

    # ─── Internal: Control helpers ────────────────────────────────────────────

    async def _control(self, device_guid: str, fields: dict) -> None:
        api_name = API_DEVICE_CONTROL_APINAME.format(device_guid=device_guid)
        body = {"status": [{"deviceGuid": device_guid, **fields}]}
        await self._transfer("POST", api_name, body=body)

    async def _zone_control(
        self, device_guid: str, zone_id: int, fields: dict
    ) -> None:
        api_name = API_DEVICE_CONTROL_APINAME.format(device_guid=device_guid)
        body = {
            "status": [
                {
                    "deviceGuid": device_guid,
                    "zoneStatus": [{"zoneId": zone_id, **fields}],
                }
            ]
        }
        await self._transfer("POST", api_name, body=body)

    async def _tank_control(self, device_guid: str, fields: dict) -> None:
        api_name = API_DEVICE_CONTROL_APINAME.format(device_guid=device_guid)
        body = {
            "status": [{"deviceGuid": device_guid, "tankStatus": [fields]}]
        }
        await self._transfer("POST", api_name, body=body)

    # ─── Internal: Transfer proxy ─────────────────────────────────────────────

    async def _transfer(
        self,
        method: str,
        api_name: str,
        body: dict | None = None,
    ) -> dict[str, Any]:
        """Call the Aquarea transfer proxy endpoint."""
        url = f"{API_BASE_URL}{API_TRANSFER_PATH}"
        payload: dict[str, Any] = {
            "apiName": api_name,
            "requestMethod": method,
        }
        if body is not None:
            payload["requestBody"] = body

        return await self._api_post(url, payload)

    # ─── Internal: Low-level API requests ─────────────────────────────────────

    async def _api_get(self, url: str) -> dict[str, Any]:
        try:
            async with self._session.get(
                url, headers=self._api_headers(), ssl=True
            ) as resp:
                await self._check_api_response(resp)
                return await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise AquareaConnectionError(str(exc)) from exc

    async def _api_post(self, url: str, payload: dict) -> dict[str, Any]:
        try:
            async with self._session.post(
                url, json=payload, headers=self._api_headers(), ssl=True
            ) as resp:
                await self._check_api_response(resp)
                if resp.status == 204:
                    return {}
                return await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise AquareaConnectionError(str(exc)) from exc

    async def _check_api_response(self, resp: aiohttp.ClientResponse) -> None:
        if resp.status == 401:
            raise AquareaAuthError("Access token expired – re-authentication required")
        if resp.status not in (200, 204):
            body = await resp.text()
            raise AquareaApiError(
                f"API error {resp.status} at {resp.url}: {body[:300]}"
            )
        # Aquarea returns 200 even for errors; check for error codes in body
        # (handled by callers when needed)

    def _api_headers(self) -> dict[str, str]:
        return {
            "User-Agent": API_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-app-type": API_APP_TYPE,
            "x-app-version": API_APP_VERSION,
            "x-user-authorization-v2": f"Bearer {self._access_token}",
        }

    # ─── Internal: OAuth2 PKCE flow ───────────────────────────────────────────

    async def _oauth_authorize(self, challenge: str, state: str) -> str:
        """Step 1 – GET /authorize and return the _csrf cookie value."""
        params = {
            "client_id": APP_CLIENT_ID,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "redirect_uri": APP_REDIRECT_URI,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "audience": OAUTH_AUDIENCE,
        }
        url = (
            f"{AUTH_BASE_URL}{AUTH_BASE_URL.split('/')[-1]}"  # keep base clean
        )
        url = f"{AUTH_BASE_URL}/authorize?{urlencode(params)}"

        async with self._session.get(
            url,
            headers={"User-Agent": AUTH_USER_AGENT, "Auth0-Client": AUTH0_CLIENT_B64},
            ssl=True,
            allow_redirects=True,
        ) as resp:
            if resp.status not in (200, 302):
                body = await resp.text()
                raise AquareaAuthError(
                    f"OAuth authorize failed ({resp.status}): {body[:200]}"
                )

        # Extract _csrf from cookie jar
        for cookie in self._session.cookie_jar:
            if cookie.key == "_csrf":
                return cookie.value

        raise AquareaAuthError(
            "No _csrf cookie received from OAuth authorize endpoint"
        )

    async def _oauth_credentials(
        self,
        username: str,
        password: str,
        csrf: str,
        state: str,
        challenge: str,
    ) -> dict[str, str]:
        """Step 2 – POST credentials; return hidden form fields from the response."""
        url = f"{AUTH_BASE_URL}{AUTH_LOGIN_PATH}"
        payload = {
            "client_id": APP_CLIENT_ID,
            "redirect_uri": APP_REDIRECT_URI,
            "tenant": OAUTH_TENANT,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "audience": OAUTH_AUDIENCE,
            "_csrf": csrf,
            "state": state,
            "username": username,
            "password": password,
            "lang": "en",
            "connection": "PanasonicID-Authentication",
        }
        headers = {
            "Content-Type": "application/json",
            "Auth0-Client": AUTH0_CLIENT_B64,
            "User-Agent": AUTH_USER_AGENT,
        }

        async with self._session.post(
            url, json=payload, headers=headers, ssl=True, allow_redirects=True
        ) as resp:
            body = await resp.text()

        if resp.status == 401 or '"error"' in body.lower():
            raise AquareaAuthError("Invalid username or password")

        if resp.status not in (200, 302):
            raise AquareaAuthError(
                f"Credentials step failed ({resp.status}): {body[:200]}"
            )

        parser = _HiddenFormParser()
        parser.feed(body)
        if not parser.fields:
            raise AquareaAuthError(
                "No hidden form fields in login response – "
                "check username/password or API changes"
            )
        _LOGGER.debug("Callback form fields: %s", list(parser.fields.keys()))
        return parser.fields

    async def _oauth_callback(self, form_fields: dict[str, str]) -> str:
        """Step 3 – POST form to callback URL; return the OAuth authorization code."""
        url = f"{AUTH_BASE_URL}{AUTH_CALLBACK_PATH}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": AUTH_USER_AGENT,
        }

        # Follow HTTP redirects manually; stop at custom URI scheme
        redirect = url
        data: str | None = urlencode(form_fields)
        method = "POST"

        for _ in range(10):  # safety limit
            req_kw: dict[str, Any] = {
                "headers": headers,
                "ssl": True,
                "allow_redirects": False,
            }
            if method == "POST" and data is not None:
                req_kw["data"] = data

            async with self._session.request(method, redirect, **req_kw) as resp:
                location = resp.headers.get("Location", "")

            if not location:
                raise AquareaAuthError(
                    "OAuth callback chain ended without reaching the redirect URI"
                )

            if location.startswith(APP_REDIRECT_URI.split("://")[0] + "://"):
                # Custom URI scheme – extract the code
                parsed = urlparse(location)
                params = parse_qs(parsed.query)
                code_list = params.get("code")
                if not code_list:
                    raise AquareaAuthError(
                        f"No authorization code in redirect URL: {location}"
                    )
                return code_list[0]

            # Standard HTTP redirect
            redirect = (
                location
                if location.startswith("http")
                else f"{AUTH_BASE_URL}{location}"
            )
            method = "GET"
            data = None
            headers = {"User-Agent": AUTH_USER_AGENT}

        raise AquareaAuthError("OAuth callback redirect limit exceeded")

    async def _oauth_token(self, code: str, verifier: str) -> dict[str, Any]:
        """Step 4 – Exchange authorization code for access token."""
        url = f"{AUTH_BASE_URL}{AUTH_TOKEN_PATH}"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": APP_REDIRECT_URI,
            "client_id": APP_CLIENT_ID,
        }
        headers = {
            "Content-Type": "application/json",
            "Auth0-Client": AUTH0_CLIENT_B64,
            "User-Agent": AUTH_USER_AGENT,
        }

        async with self._session.post(
            url, json=payload, headers=headers, ssl=True
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise AquareaAuthError(
                    f"Token exchange failed ({resp.status}): {body[:200]}"
                )
            data = await resp.json(content_type=None)

        if "access_token" not in data:
            raise AquareaAuthError(
                f"No access_token in token response: {list(data.keys())}"
            )
        return data

    async def _get_acc_client_id(self) -> str | None:
        """Step 5 – POST to accsmart login to obtain the Panasonic client ID."""
        url = f"{API_BASE_URL}{API_ACC_LOGIN_PATH}"
        headers = {
            "User-Agent": API_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-app-type": API_APP_TYPE,
            "x-app-version": API_APP_VERSION,
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with self._session.post(
                url, json={}, headers=headers, ssl=True
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "Could not retrieve Panasonic client ID (%s)", resp.status
                    )
                    return None
                data = await resp.json(content_type=None)
                return data.get("clientId")
        except aiohttp.ClientError as exc:
            _LOGGER.warning("Client ID retrieval failed: %s", exc)
            return None
