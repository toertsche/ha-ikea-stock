"""Sensor: Bestand (Qty) je Markt."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IkeaStockConfigEntry, IkeaStockCoordinator
from .entity import IkeaStockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IkeaStockConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(StockQuantitySensor(coordinator, s) for s in coordinator.selected_stores)


class StockQuantitySensor(IkeaStockEntity, SensorEntity):
    """Anzahl im Markt."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:package-variant"

    def __init__(self, coordinator: IkeaStockCoordinator, store: str) -> None:
        super().__init__(coordinator, store, "stock")

    @property
    def native_value(self) -> int | None:
        return self.quantity
