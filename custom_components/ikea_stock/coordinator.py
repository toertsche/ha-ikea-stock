"""DataUpdateCoordinator: Abruf, Wechselerkennung 0 -> >0, Benachrichtigung."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import StockApiError, async_fetch_stock
from .const import (
    CONF_COUNTRY,
    CONF_ITEM_NO,
    CONF_NOTIFY_ENTITY,
    CONF_PERSISTENT,
    CONF_SCAN_INTERVAL,
    CONF_STORES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_AVAILABLE,
    MIN_SCAN_INTERVAL,
    storage_key,
)
from .parser import StockPage, StockParseError

_LOGGER = logging.getLogger(__name__)

_TEXTS = {
    "de": ("IKEA: {name} verfügbar", "{name} ist bei IKEA {store} verfügbar (Bestand: {qty})."),
    "en": ("IKEA: {name} in stock", "{name} is in stock at IKEA {store} (qty: {qty})."),
}


class IkeaStockCoordinator(DataUpdateCoordinator[StockPage]):
    """Holt den Bestand für einen Artikel in einem Land (ein Request für alle Märkte)."""

    config_entry: IkeaStockConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        minutes = max(
            MIN_SCAN_INTERVAL, int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.unique_id}",
            update_interval=timedelta(minutes=minutes),
        )
        self._store: Store[dict[str, int]] = Store(hass, 1, storage_key(entry.entry_id))
        self._previous: dict[str, int] | None = None

    @property
    def selected_stores(self) -> list[str]:
        return list(self.config_entry.options.get(CONF_STORES, []))

    async def _async_setup(self) -> None:
        self._previous = await self._store.async_load()

    async def _async_update_data(self) -> StockPage:
        entry = self.config_entry
        try:
            page = await async_fetch_stock(
                async_get_clientsession(self.hass),
                entry.data[CONF_COUNTRY],
                entry.data[CONF_ITEM_NO],
            )
        except (StockApiError, StockParseError) as err:
            raise UpdateFailed(str(err)) from err

        await self._async_handle_transitions(page)
        return page

    async def _async_handle_transitions(self, page: StockPage) -> None:
        current = dict(page.stores)

        if self._previous is None:
            # Erstinstallation: Basisstand setzen, keine Meldung für Altbestand.
            self._previous = current
            await self._store.async_save(current)
            return

        newly = {
            store: current[store]
            for store in self.selected_stores
            if current.get(store, 0) > 0 and self._previous.get(store, 0) == 0
        }
        self._previous = current
        await self._store.async_save(current)

        for store, qty in newly.items():
            await self._async_announce(page, store, qty)

    async def _async_announce(self, page: StockPage, store: str, qty: int) -> None:
        entry = self.config_entry
        name = page.product_name or entry.data[CONF_ITEM_NO]

        self.hass.bus.async_fire(
            EVENT_AVAILABLE,
            {
                "entry_id": entry.entry_id,
                "country": entry.data[CONF_COUNTRY],
                "item_no": entry.data[CONF_ITEM_NO],
                "product_name": name,
                "store": store,
                "quantity": qty,
            },
        )

        lang = "de" if self.hass.config.language.startswith("de") else "en"
        title_t, msg_t = _TEXTS[lang]
        title = title_t.format(name=name)
        message = msg_t.format(name=name, store=store, qty=qty)

        if entry.options.get(CONF_PERSISTENT, True):
            persistent_notification.async_create(
                self.hass,
                message,
                title=title,
                notification_id=f"{DOMAIN}_{entry.entry_id}_{store}",
            )

        if notify_entity := entry.options.get(CONF_NOTIFY_ENTITY):
            try:
                await self.hass.services.async_call(
                    "notify",
                    "send_message",
                    {"entity_id": notify_entity, "title": title, "message": message},
                    blocking=True,
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Benachrichtigung über %s fehlgeschlagen: %s", notify_entity, err)


type IkeaStockConfigEntry = ConfigEntry[IkeaStockCoordinator]
