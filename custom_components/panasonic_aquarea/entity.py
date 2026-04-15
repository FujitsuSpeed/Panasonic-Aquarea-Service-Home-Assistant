"""Base entity for Panasonic Aquarea."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AquareaDataUpdateCoordinator


class AquareaBaseEntity(CoordinatorEntity[AquareaDataUpdateCoordinator]):
    """Base class for all Aquarea entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AquareaDataUpdateCoordinator,
        unique_id_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_guid}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_guid)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=self._get_model(),
            sw_version=self._get_firmware(),
        )

    def _get_model(self) -> str | None:
        return self.coordinator.data.get("deviceModel")

    def _get_firmware(self) -> str | None:
        return self.coordinator.data.get("firmwareVersion")

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
        )
