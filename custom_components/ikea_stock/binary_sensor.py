"""Binärsensor: Artikel im Markt verfügbar (Qty > 0)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    async_add_entities(StockAvailableSensor(coordinator, s) for s in coordinator.selected_stores)


class StockAvailableSensor(IkeaStockEntity, BinarySensorEntity):
    """An, sobald Qty > 0."""

    _attr_icon = "mdi:store-check"

    def __init__(self, coordinator: IkeaStockCoordinator, store: str) -> None:
        super().__init__(coordinator, store, "available")

    @property
    def is_on(self) -> bool | None:
        qty = self.quantity
        return None if qty is None else qty > 0
