"""Config- und Options-Flow: Land + Artikelnummer, dann Märkte, Intervall, Benachrichtigung."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import StockApiError, async_fetch_stock
from .const import (
    CONF_COUNTRY,
    CONF_ITEM_NO,
    CONF_NOTIFY_ENTITY,
    CONF_PERSISTENT,
    CONF_SCAN_INTERVAL,
    CONF_STORES,
    COUNTRIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .parser import ItemNotFoundError, StockPage, StockParseError


def _options_schema(stores: list[str], defaults: dict[str, Any]) -> vol.Schema:
    """Gemeinsames Formular für Erst-Einrichtung und Optionen."""
    notify = defaults.get(CONF_NOTIFY_ENTITY)
    return vol.Schema(
        {
            vol.Required(CONF_STORES, default=defaults.get(CONF_STORES, [])): SelectSelector(
                SelectSelectorConfig(
                    options=sorted(stores), multiple=True, mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    unit_of_measurement="min",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_NOTIFY_ENTITY, description={"suggested_value": notify}
            ): EntitySelector(EntitySelectorConfig(domain="notify")),
            vol.Required(
                CONF_PERSISTENT, default=defaults.get(CONF_PERSISTENT, True)
            ): BooleanSelector(),
        }
    )


def _clean_options(user_input: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {
        CONF_STORES: list(user_input[CONF_STORES]),
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
        CONF_PERSISTENT: bool(user_input[CONF_PERSISTENT]),
    }
    if user_input.get(CONF_NOTIFY_ENTITY):
        options[CONF_NOTIFY_ENTITY] = user_input[CONF_NOTIFY_ENTITY]
    return options


def _country_matches(code: str, page: StockPage) -> bool:
    """Land aus der Ergebnisüberschrift muss zur Auswahl passen (Fehlt es: lenient)."""
    if page.country_name is None:
        return True
    return page.country_name.casefold() == COUNTRIES.get(code, "").casefold()


class IkeaStockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung: Land/Artikel prüfen, dann Märkte wählen."""

    VERSION = 1

    def __init__(self) -> None:
        self._country = ""
        self._item_no = ""
        self._page: StockPage | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> IkeaStockOptionsFlow:  # noqa: ANN001
        return IkeaStockOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            country = user_input[CONF_COUNTRY]
            item_no = re.sub(r"\D", "", user_input[CONF_ITEM_NO])  # "806.220.62" -> 80622062

            if len(item_no) != 8:
                errors[CONF_ITEM_NO] = "invalid_item"
            else:
                await self.async_set_unique_id(f"{country}_{item_no}")
                self._abort_if_unique_id_configured()
                try:
                    page = await async_fetch_stock(
                        async_get_clientsession(self.hass), country, item_no
                    )
                except StockApiError:
                    errors["base"] = "cannot_connect"
                except ItemNotFoundError:
                    errors["base"] = "item_not_in_country"
                except StockParseError:
                    errors["base"] = "no_stock_data"
                else:
                    if not _country_matches(country, page):
                        errors[CONF_COUNTRY] = "country_mismatch"
                    else:
                        self._country, self._item_no, self._page = country, item_no, page
                        return await self.async_step_stores()

        default_country = (self.hass.config.country or "DE").lower()
        if default_country not in COUNTRIES:
            default_country = "de"

        schema = vol.Schema(
            {
                vol.Required(CONF_COUNTRY, default=default_country): SelectSelector(
                    SelectSelectorConfig(
                        options=[SelectOptionDict(value=c, label=n) for c, n in COUNTRIES.items()],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_ITEM_NO): TextSelector(),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_stores(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._page is not None  # nur nach erfolgreichem Schritt 1 erreichbar
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_STORES]:
                errors[CONF_STORES] = "no_store_selected"
            else:
                name = self._page.product_name or self._item_no
                return self.async_create_entry(
                    title=f"{name} ({self._country.upper()})",
                    data={CONF_COUNTRY: self._country, CONF_ITEM_NO: self._item_no},
                    options=_clean_options(user_input),
                )

        return self.async_show_form(
            step_id="stores",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(list(self._page.stores), {}), user_input
            ),
            description_placeholders={"product": self._page.product_name or self._item_no},
            errors=errors,
        )


class IkeaStockOptionsFlow(OptionsFlow):
    """Märkte, Intervall und Benachrichtigung nachträglich ändern."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_STORES]:
                errors[CONF_STORES] = "no_store_selected"
            else:
                return self.async_create_entry(data=_clean_options(user_input))

        known = set(entry.options.get(CONF_STORES, []))
        if entry.state is ConfigEntryState.LOADED:
            known |= set(entry.runtime_data.data.stores)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(list(known), dict(entry.options)), user_input
            ),
            errors=errors,
        )
