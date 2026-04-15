"""Sensor platform for Panasonic Aquarea."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
)
from .coordinator import AquareaDataUpdateCoordinator
from .entity import AquareaBaseEntity

_LOGGER = logging.getLogger(__name__)

_OPERATION_MODE_NAMES: dict[int, str] = {
    OPERATION_MODE_HEAT: "Heat",
    OPERATION_MODE_COOL: "Cool",
    OPERATION_MODE_AUTO: "Auto",
    OPERATION_MODE_DHW: "Hot Water Only",
    OPERATION_MODE_HEAT_DHW: "Heat + Hot Water",
    OPERATION_MODE_COOL_DHW: "Cool + Hot Water",
    OPERATION_MODE_AUTO_DHW: "Auto + Hot Water",
}


@dataclass(frozen=True, kw_only=True)
class AquareaSensorDescription(SensorEntityDescription):
    """Extended sensor description with a value extractor."""

    value_fn: Callable[[dict[str, Any]], Any]
    available_fn: Callable[[dict[str, Any]], bool] = lambda _: True


# ─── Device-level sensors ─────────────────────────────────────────────────────

DEVICE_SENSORS: tuple[AquareaSensorDescription, ...] = (
    AquareaSensorDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("outdoorNow"),
    ),
    AquareaSensorDescription(
        key="operation_mode",
        name="Operation Mode",
        icon="mdi:heat-pump",
        value_fn=lambda d: _OPERATION_MODE_NAMES.get(
            d.get("operationMode", -1), "Unknown"
        ),
    ),
    AquareaSensorDescription(
        key="error_status",
        name="Error Status",
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.get("errorStatus") or "None",
    ),
)

# ─── Zone sensors (one set per zone) ─────────────────────────────────────────

ZONE_SENSORS: tuple[AquareaSensorDescription, ...] = (
    AquareaSensorDescription(
        key="water_temperature",
        name="Water Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda z: z.get("waterTemperature"),
    ),
    AquareaSensorDescription(
        key="room_temperature",
        name="Room Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda z: z.get("roomTemperature"),
        available_fn=lambda z: z.get("roomTemperature") is not None,
    ),
)

# ─── Tank sensors ─────────────────────────────────────────────────────────────

TANK_SENSORS: tuple[AquareaSensorDescription, ...] = (
    AquareaSensorDescription(
        key="tank_temperature",
        name="Tank Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.get("temparatureNow") or t.get("temperatureNow"),
    ),
    AquareaSensorDescription(
        key="tank_setpoint",
        name="Tank Setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.get("heatSet"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: AquareaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    status = coordinator.data
    entities: list[SensorEntity] = []

    # Device-level sensors
    for desc in DEVICE_SENSORS:
        entities.append(AquareaDeviceSensor(coordinator, desc))

    # Zone sensors
    for zone in status.get("zoneStatus", []):
        zone_id: int = zone["zoneId"]
        for desc in ZONE_SENSORS:
            entities.append(AquareaZoneSensor(coordinator, desc, zone_id))

    # Tank sensors
    if status.get("tankStatus"):
        for desc in TANK_SENSORS:
            entities.append(AquareaTankSensor(coordinator, desc))

    async_add_entities(entities)


class AquareaDeviceSensor(AquareaBaseEntity, SensorEntity):
    """Sensor for device-level data."""

    entity_description: AquareaSensorDescription

    def __init__(
        self,
        coordinator: AquareaDataUpdateCoordinator,
        description: AquareaSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.entity_description.available_fn(self.coordinator.data)
        )


class AquareaZoneSensor(AquareaBaseEntity, SensorEntity):
    """Sensor for zone-level data."""

    entity_description: AquareaSensorDescription

    def __init__(
        self,
        coordinator: AquareaDataUpdateCoordinator,
        description: AquareaSensorDescription,
        zone_id: int,
    ) -> None:
        super().__init__(coordinator, f"zone_{zone_id}_{description.key}")
        self.entity_description = description
        self._zone_id = zone_id
        self._attr_name = f"Zone {zone_id} {description.name}"

    @property
    def _zone(self) -> dict:
        for zone in self.coordinator.data.get("zoneStatus", []):
            if zone["zoneId"] == self._zone_id:
                return zone
        return {}

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._zone)

    @property
    def available(self) -> bool:
        return (
            super().available
            and bool(self._zone)
            and self.entity_description.available_fn(self._zone)
        )


class AquareaTankSensor(AquareaBaseEntity, SensorEntity):
    """Sensor for tank-level data."""

    entity_description: AquareaSensorDescription

    def __init__(
        self,
        coordinator: AquareaDataUpdateCoordinator,
        description: AquareaSensorDescription,
    ) -> None:
        super().__init__(coordinator, f"tank_{description.key}")
        self.entity_description = description
        self._attr_name = f"Tank {description.name}"

    @property
    def _tank(self) -> dict:
        tanks: list[dict] = self.coordinator.data.get("tankStatus", [])
        return tanks[0] if tanks else {}

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._tank)

    @property
    def available(self) -> bool:
        return (
            super().available
            and bool(self._tank)
            and self.entity_description.available_fn(self._tank)
        )
