"""Climate platform for Panasonic Aquarea – controls heating/cooling zones."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COORDINATOR,
    DOMAIN,
    OPERATION_MODE_AUTO,
    OPERATION_MODE_AUTO_DHW,
    OPERATION_MODE_COOL,
    OPERATION_MODE_COOL_DHW,
    OPERATION_MODE_DHW,
    OPERATION_MODE_HEAT,
    OPERATION_MODE_HEAT_DHW,
    OPERATION_STATUS_OFF,
    OPERATION_STATUS_ON,
    ZONE_COOL_TEMP_MAX,
    ZONE_COOL_TEMP_MIN,
    ZONE_CTRL_ROOM_TEMP,
    ZONE_CTRL_WATER_TEMP,
    ZONE_HEAT_TEMP_MAX,
    ZONE_HEAT_TEMP_MIN,
    ZONE_ROOM_COOL_TEMP_MAX,
    ZONE_ROOM_COOL_TEMP_MIN,
    ZONE_ROOM_HEAT_TEMP_MAX,
    ZONE_ROOM_HEAT_TEMP_MIN,
)
from .coordinator import AquareaDataUpdateCoordinator
from .entity import AquareaBaseEntity

_LOGGER = logging.getLogger(__name__)

# Map Aquarea operation modes → HA HVAC modes
_AQUAREA_TO_HVAC: dict[int, HVACMode] = {
    OPERATION_MODE_HEAT: HVACMode.HEAT,
    OPERATION_MODE_COOL: HVACMode.COOL,
    OPERATION_MODE_AUTO: HVACMode.AUTO,
    OPERATION_MODE_DHW: HVACMode.OFF,      # DHW only → zone is OFF
    OPERATION_MODE_HEAT_DHW: HVACMode.HEAT,
    OPERATION_MODE_COOL_DHW: HVACMode.COOL,
    OPERATION_MODE_AUTO_DHW: HVACMode.AUTO,
}

# When turning on from HA, prefer "mode + DHW" variants when tank exists
_HVAC_TO_AQUAREA: dict[HVACMode, int] = {
    HVACMode.HEAT: OPERATION_MODE_HEAT_DHW,
    HVACMode.COOL: OPERATION_MODE_COOL_DHW,
    HVACMode.AUTO: OPERATION_MODE_AUTO_DHW,
    HVACMode.OFF: OPERATION_STATUS_OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities from a config entry."""
    coordinator: AquareaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    status = coordinator.data

    zone_statuses: list[dict] = status.get("zoneStatus", [])
    entities = [
        AquareaZoneClimate(coordinator, zone)
        for zone in zone_statuses
    ]
    async_add_entities(entities)


class AquareaZoneClimate(AquareaBaseEntity, ClimateEntity):
    """Climate entity representing one heating/cooling zone."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]

    def __init__(
        self,
        coordinator: AquareaDataUpdateCoordinator,
        zone: dict,
    ) -> None:
        zone_id: int = zone["zoneId"]
        super().__init__(coordinator, f"zone_{zone_id}_climate")
        self._zone_id = zone_id
        self._attr_name = f"Zone {zone_id}"
        self._attr_translation_key = f"zone_{zone_id}"

    # ─── Zone data helper ─────────────────────────────────────────────────────

    @property
    def _zone(self) -> dict:
        for zone in self.coordinator.data.get("zoneStatus", []):
            if zone["zoneId"] == self._zone_id:
                return zone
        return {}

    @property
    def _control_mode(self) -> int:
        return self._zone.get("heatCool", ZONE_CTRL_WATER_TEMP)

    # ─── HVAC state ──────────────────────────────────────────────────────────

    @property
    def hvac_mode(self) -> HVACMode:
        data = self.coordinator.data
        device_on = data.get("operationStatus", OPERATION_STATUS_OFF) == OPERATION_STATUS_ON
        zone_on = self._zone.get("operationStatus", OPERATION_STATUS_OFF) == OPERATION_STATUS_ON

        if not device_on or not zone_on:
            return HVACMode.OFF

        op_mode: int = data.get("operationMode", OPERATION_MODE_HEAT_DHW)
        return _AQUAREA_TO_HVAC.get(op_mode, HVACMode.AUTO)

    # ─── Temperatures ─────────────────────────────────────────────────────────

    @property
    def current_temperature(self) -> float | None:
        zone = self._zone
        if self._control_mode == ZONE_CTRL_ROOM_TEMP:
            return zone.get("roomTemperature")
        return zone.get("waterTemperature")

    @property
    def target_temperature(self) -> float | None:
        zone = self._zone
        hvac = self.hvac_mode

        if self._control_mode == ZONE_CTRL_ROOM_TEMP:
            if hvac == HVACMode.COOL:
                return zone.get("coolRoomSetTemp")
            return zone.get("heatRoomSetTemp")
        else:
            if hvac == HVACMode.COOL:
                return zone.get("coolTemperature")
            return zone.get("heatTemperature")

    @property
    def min_temp(self) -> float:
        hvac = self.hvac_mode
        if self._control_mode == ZONE_CTRL_ROOM_TEMP:
            return ZONE_ROOM_COOL_TEMP_MIN if hvac == HVACMode.COOL else ZONE_ROOM_HEAT_TEMP_MIN
        return ZONE_COOL_TEMP_MIN if hvac == HVACMode.COOL else ZONE_HEAT_TEMP_MIN

    @property
    def max_temp(self) -> float:
        hvac = self.hvac_mode
        if self._control_mode == ZONE_CTRL_ROOM_TEMP:
            return ZONE_ROOM_COOL_TEMP_MAX if hvac == HVACMode.COOL else ZONE_ROOM_HEAT_TEMP_MAX
        return ZONE_COOL_TEMP_MAX if hvac == HVACMode.COOL else ZONE_HEAT_TEMP_MAX

    @property
    def target_temperature_step(self) -> float:
        return 0.5

    # ─── Control ─────────────────────────────────────────────────────────────

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        client = self.coordinator.client
        guid = self.coordinator.device_guid

        if hvac_mode == HVACMode.OFF:
            await client.set_operation_status(guid, OPERATION_STATUS_OFF)
        else:
            aquarea_mode = _HVAC_TO_AQUAREA[hvac_mode]
            # Turn device on if it was off
            if self.coordinator.data.get("operationStatus") == OPERATION_STATUS_OFF:
                await client.set_operation_status(guid, OPERATION_STATUS_ON)
            await client.set_operation_mode(guid, aquarea_mode)

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp: float = kwargs[ATTR_TEMPERATURE]
        client = self.coordinator.client
        guid = self.coordinator.device_guid
        hvac = self.hvac_mode

        if self._control_mode == ZONE_CTRL_ROOM_TEMP:
            if hvac == HVACMode.COOL:
                await client.set_zone_room_cool_temperature(guid, self._zone_id, temp)
            else:
                await client.set_zone_room_heat_temperature(guid, self._zone_id, temp)
        else:
            if hvac == HVACMode.COOL:
                await client.set_zone_cool_temperature(guid, self._zone_id, temp)
            else:
                await client.set_zone_heat_temperature(guid, self._zone_id, temp)

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    # ─── Extra state attributes ───────────────────────────────────────────────

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        zone = self._zone
        return {
            "control_mode": zone.get("heatCool"),
            "water_temperature": zone.get("waterTemperature"),
            "room_temperature": zone.get("roomTemperature"),
            "heat_setpoint_water": zone.get("heatTemperature"),
            "cool_setpoint_water": zone.get("coolTemperature"),
            "heat_setpoint_room": zone.get("heatRoomSetTemp"),
            "cool_setpoint_room": zone.get("coolRoomSetTemp"),
        }
