"""Water heater platform for Panasonic Aquarea – domestic hot-water tank."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COORDINATOR,
    DOMAIN,
    OPERATION_STATUS_OFF,
    OPERATION_STATUS_ON,
    TANK_BOOST_OFF,
    TANK_BOOST_ON,
    TANK_TEMP_MAX,
    TANK_TEMP_MIN,
)
from .coordinator import AquareaDataUpdateCoordinator
from .entity import AquareaBaseEntity

_LOGGER = logging.getLogger(__name__)

STATE_PERFORMANCE = "performance"   # Boost / force heating
STATE_ECO = "eco"                   # Normal tank heating
OPERATION_LIST = [STATE_OFF, STATE_ECO, STATE_PERFORMANCE]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the water heater entity from a config entry."""
    coordinator: AquareaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]

    tank_statuses: list[dict] = coordinator.data.get("tankStatus", [])
    if not tank_statuses:
        _LOGGER.debug("No tank found for device %s", coordinator.device_guid)
        return

    async_add_entities([AquareaTankWaterHeater(coordinator)])


class AquareaTankWaterHeater(AquareaBaseEntity, WaterHeaterEntity):
    """Water heater entity for the domestic hot-water tank."""

    _attr_name = "Hot Water Tank"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = TANK_TEMP_MIN
    _attr_max_temp = TANK_TEMP_MAX
    _attr_target_temperature_step = 1.0
    _attr_operation_list = OPERATION_LIST
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.AWAY_MODE
    )

    def __init__(self, coordinator: AquareaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "tank_water_heater")

    # ─── Tank data helper ─────────────────────────────────────────────────────

    @property
    def _tank(self) -> dict:
        tanks: list[dict] = self.coordinator.data.get("tankStatus", [])
        return tanks[0] if tanks else {}

    # ─── State ───────────────────────────────────────────────────────────────

    @property
    def current_temperature(self) -> float | None:
        # The Panasonic API has a typo: "temparatureNow"
        return self._tank.get("temparatureNow") or self._tank.get("temperatureNow")

    @property
    def target_temperature(self) -> float | None:
        return self._tank.get("heatSet")

    @property
    def current_operation(self) -> str:
        tank = self._tank
        if tank.get("operationStatus", OPERATION_STATUS_OFF) == OPERATION_STATUS_OFF:
            return STATE_OFF
        if tank.get("boostHeat", TANK_BOOST_OFF) == TANK_BOOST_ON:
            return STATE_PERFORMANCE
        return STATE_ECO

    # ─── Away / Holiday mode ─────────────────────────────────────────────────

    @property
    def is_away_mode_on(self) -> bool:
        return (
            self.coordinator.data.get("holidayTimer", 0) == 1
        )

    # ─── Control ─────────────────────────────────────────────────────────────

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp: float = kwargs.get("temperature", self.target_temperature)
        await self.coordinator.client.set_tank_temperature(
            self.coordinator.device_guid, temp
        )
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        client = self.coordinator.client
        guid = self.coordinator.device_guid

        if operation_mode == STATE_OFF:
            await client.set_tank_operation_status(guid, OPERATION_STATUS_OFF)
            await client.set_tank_boost(guid, TANK_BOOST_OFF)
        elif operation_mode == STATE_PERFORMANCE:
            await client.set_tank_operation_status(guid, OPERATION_STATUS_ON)
            await client.set_tank_boost(guid, TANK_BOOST_ON)
        else:  # eco / normal
            await client.set_tank_operation_status(guid, OPERATION_STATUS_ON)
            await client.set_tank_boost(guid, TANK_BOOST_OFF)

        await self.coordinator.async_request_refresh()

    async def async_turn_away_mode_on(self) -> None:
        await self.coordinator.client.set_holiday_mode(
            self.coordinator.device_guid, 1
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_away_mode_off(self) -> None:
        await self.coordinator.client.set_holiday_mode(
            self.coordinator.device_guid, 0
        )
        await self.coordinator.async_request_refresh()

    # ─── Extra state attributes ───────────────────────────────────────────────

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tank = self._tank
        return {
            "boost_active": tank.get("boostHeat") == TANK_BOOST_ON,
            "tank_operation_status": tank.get("operationStatus"),
        }
