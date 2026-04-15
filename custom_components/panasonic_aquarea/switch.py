"""Switch platform for Panasonic Aquarea."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COORDINATOR,
    DOMAIN,
    FORCE_HEATER_OFF,
    FORCE_HEATER_ON,
    HOLIDAY_MODE_OFF,
    HOLIDAY_MODE_ON,
    TANK_BOOST_OFF,
    TANK_BOOST_ON,
)
from .coordinator import AquareaDataUpdateCoordinator
from .entity import AquareaBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AquareaSwitchDescription(SwitchEntityDescription):
    """Switch description with value extractor and control callbacks."""

    is_on_fn: Callable[[dict[str, Any]], bool]
    turn_on_fn: Callable[..., Any]
    turn_off_fn: Callable[..., Any]
    available_fn: Callable[[dict[str, Any]], bool] = lambda _: True


def _tank_boost_on(client, guid):
    return client.set_tank_boost(guid, TANK_BOOST_ON)

def _tank_boost_off(client, guid):
    return client.set_tank_boost(guid, TANK_BOOST_OFF)

def _force_heater_on(client, guid):
    return client.set_force_heater(guid, FORCE_HEATER_ON)

def _force_heater_off(client, guid):
    return client.set_force_heater(guid, FORCE_HEATER_OFF)

def _holiday_on(client, guid):
    return client.set_holiday_mode(guid, HOLIDAY_MODE_ON)

def _holiday_off(client, guid):
    return client.set_holiday_mode(guid, HOLIDAY_MODE_OFF)


SWITCH_DESCRIPTIONS: tuple[AquareaSwitchDescription, ...] = (
    AquareaSwitchDescription(
        key="tank_boost",
        name="Tank Boost Heating",
        icon="mdi:water-boiler",
        is_on_fn=lambda d: (
            bool(d.get("tankStatus"))
            and d["tankStatus"][0].get("boostHeat", TANK_BOOST_OFF) == TANK_BOOST_ON
        ),
        turn_on_fn=_tank_boost_on,
        turn_off_fn=_tank_boost_off,
        available_fn=lambda d: bool(d.get("tankStatus")),
    ),
    AquareaSwitchDescription(
        key="force_heater",
        name="Auxiliary Heater",
        icon="mdi:radiator",
        is_on_fn=lambda d: d.get("forceHeater", FORCE_HEATER_OFF) == FORCE_HEATER_ON,
        turn_on_fn=_force_heater_on,
        turn_off_fn=_force_heater_off,
    ),
    AquareaSwitchDescription(
        key="holiday_mode",
        name="Holiday Mode",
        icon="mdi:airplane",
        is_on_fn=lambda d: d.get("holidayTimer", HOLIDAY_MODE_OFF) == HOLIDAY_MODE_ON,
        turn_on_fn=_holiday_on,
        turn_off_fn=_holiday_off,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    coordinator: AquareaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    async_add_entities(
        AquareaSwitch(coordinator, desc) for desc in SWITCH_DESCRIPTIONS
    )


class AquareaSwitch(AquareaBaseEntity, SwitchEntity):
    """A simple on/off switch for an Aquarea feature."""

    entity_description: AquareaSwitchDescription

    def __init__(
        self,
        coordinator: AquareaDataUpdateCoordinator,
        description: AquareaSwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.entity_description.available_fn(self.coordinator.data)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.turn_on_fn(
            self.coordinator.client, self.coordinator.device_guid
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.turn_off_fn(
            self.coordinator.client, self.coordinator.device_guid
        )
        await self.coordinator.async_request_refresh()
