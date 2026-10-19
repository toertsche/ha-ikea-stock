"""Integrationstests: Config-Flow, Entitäten, Wechselerkennung (Abruf gemockt).

Ausführen (mit pytest-homeassistant-custom-component):  pytest tests/
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.ikea_stock.api import StockApiError
from custom_components.ikea_stock.const import (
    CONF_COUNTRY,
    CONF_ITEM_NO,
    CONF_PERSISTENT,
    CONF_SCAN_INTERVAL,
    CONF_STORES,
    DOMAIN,
    EVENT_AVAILABLE,
)
from custom_components.ikea_stock.parser import ItemNotFoundError, StockPage, StockParseError

FETCH = "custom_components.ikea_stock.coordinator.async_fetch_stock"
FETCH_FLOW = "custom_components.ikea_stock.config_flow.async_fetch_stock"


def _page(frankfurt: int = 0, wallau: int = 0, country: str = "Germany") -> StockPage:
    return StockPage(
        product_name="LILJEBAGGE Thermostat",
        country_name=country,
        stores={"Frankfurt": frankfurt, "Wallau": wallau, "Hanau": 5},
    )


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="de_80622062",
        title="LILJEBAGGE (DE)",
        data={CONF_COUNTRY: "de", CONF_ITEM_NO: "80622062"},
        options={CONF_STORES: ["Frankfurt", "Wallau"], CONF_SCAN_INTERVAL: 30, CONF_PERSISTENT: True},
    )


async def test_config_flow_happy_path(hass: HomeAssistant) -> None:
    with patch(FETCH_FLOW, return_value=_page()), patch(FETCH, return_value=_page()):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_COUNTRY: "de", CONF_ITEM_NO: "806.220.62"}
        )
        assert result["step_id"] == "stores"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STORES: ["Frankfurt", "Wallau"],
                CONF_SCAN_INTERVAL: 15,
                CONF_PERSISTENT: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_COUNTRY: "de", CONF_ITEM_NO: "80622062"}
    assert result["options"][CONF_STORES] == ["Frankfurt", "Wallau"]
    assert result["options"][CONF_SCAN_INTERVAL] == 15
    assert hass.states.get("sensor.liljebagge_thermostat_de_frankfurt_stock") is not None


@pytest.mark.parametrize(
    ("side_effect", "item", "error_key", "error"),
    [
        (StockApiError("x"), "80622062", "base", "cannot_connect"),
        (StockParseError("x"), "80622062", "base", "no_stock_data"),
        (ItemNotFoundError("x"), "80622062", "base", "item_not_in_country"),
        (None, "1234", CONF_ITEM_NO, "invalid_item"),
    ],
)
async def test_config_flow_errors(hass, side_effect, item, error_key, error) -> None:
    with patch(FETCH_FLOW, side_effect=side_effect):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_COUNTRY: "de", CONF_ITEM_NO: item}
        )
    assert result["errors"] == {error_key: error}


async def test_config_flow_country_mismatch(hass: HomeAssistant) -> None:
    """Seite liefert Germany, gewählt war Österreich -> Ablehnung."""
    with patch(FETCH_FLOW, return_value=_page(country="Germany")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_COUNTRY: "at", CONF_ITEM_NO: "80622062"}
        )
    assert result["errors"] == {CONF_COUNTRY: "country_mismatch"}


async def test_transition_fires_event_once(hass: HomeAssistant) -> None:
    events = async_capture_events(hass, EVENT_AVAILABLE)
    entry = _entry()
    entry.add_to_hass(hass)

    # Erstlauf mit Altbestand in Frankfurt: Basisstand, KEIN Alarm
    with patch(FETCH, return_value=_page(frankfurt=3)):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert events == []
    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id("binary_sensor", DOMAIN, "de_80622062_frankfurt_available")

    async def tick(page: StockPage) -> None:
        with patch(FETCH, return_value=page):
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31 * tick.n))
            tick.n += 1
            await hass.async_block_till_done()

    tick.n = 1

    await tick(_page(frankfurt=5))  # 3 -> 5: kein Alarm
    assert events == []
    await tick(_page(frankfurt=0))  # leer
    await tick(_page(wallau=2))  # Wallau 0 -> 2: Alarm
    assert [e.data["store"] for e in events] == ["Wallau"]
    assert events[0].data["quantity"] == 2
    await tick(_page(wallau=2))  # unverändert: kein weiterer Alarm
    assert len(events) == 1

    # Hanau ist nicht ausgewählt -> kein Event, obwohl Bestand
    assert all(e.data["store"] != "Hanau" for e in events)


async def test_fetch_failure_marks_unavailable(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(FETCH, side_effect=StockApiError("down")):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state.value == "setup_retry"
