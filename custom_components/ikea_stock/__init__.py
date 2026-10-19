"""IKEA Stock Watch – Bestandsüberwachung über easyrebuild.com."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import storage_key
from .coordinator import IkeaStockConfigEntry, IkeaStockCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: IkeaStockConfigEntry) -> bool:
    """Integration für einen Artikel/Land einrichten."""
    coordinator = IkeaStockCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Änderungen an Märkten/Intervall/Benachrichtigung -> neu laden
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: IkeaStockConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: IkeaStockConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: IkeaStockConfigEntry) -> None:
    """Persistierten Letztstand beim Entfernen löschen (Datensparsamkeit)."""
    await Store(hass, 1, storage_key(entry.entry_id)).async_remove()
