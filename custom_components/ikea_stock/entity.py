"""Basisklasse der Entitäten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import BASE_URL, CONF_COUNTRY, CONF_ITEM_NO, DOMAIN
from .coordinator import IkeaStockCoordinator


class IkeaStockEntity(CoordinatorEntity[IkeaStockCoordinator]):
    """Entität für einen Markt (Store) eines Artikels."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IkeaStockCoordinator, store: str, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._store_name = store
        self._attr_unique_id = f"{entry.unique_id}_{slugify(store)}_{key}"
        self._attr_translation_key = key
        self._attr_translation_placeholders = {"store": store}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="IKEA",
            model=entry.data[CONF_ITEM_NO],
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=(
                f"{BASE_URL}?country={entry.data[CONF_COUNTRY]}&itemNo={entry.data[CONF_ITEM_NO]}"
            ),
        )

    @property
    def quantity(self) -> int | None:
        return self.coordinator.data.stores.get(self._store_name)

    @property
    def available(self) -> bool:
        return super().available and self.quantity is not None
