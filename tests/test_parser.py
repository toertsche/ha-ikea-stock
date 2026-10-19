"""Parser-Tests ohne Home-Assistant-Abhängigkeit:  python tests/test_parser.py (oder pytest).

Fixtures sind SYNTHETISCH und bilden die beobachtete Seitenstruktur nach.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    "parser_under_test",
    Path(__file__).parent.parent / "custom_components" / "ikea_stock" / "parser.py",
)
parser = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = parser  # dataclasses braucht das Modul in sys.modules
_spec.loader.exec_module(parser)  # type: ignore[union-attr]


def _row(store: str, qty: int) -> str:
    # Struktur wie im echten DOM (per Browser verifiziert, 2026-10-19)
    return (
        '<tr class="align-middle expandable-row" data-bs-toggle="collapse" style="cursor: pointer;">\n'
        f'  <td>IKEA {store}</td>\n  <td class=""> {qty} </td>\n  <td class="text-success"> </td>\n'
        '  <td> <i class="bi bi-calendar-x" title="N/A"></i> </td>\n</tr>\n'
        '<tr class="collapse text-start" id="details-1"><td colspan="4"><div class="card card-body">'
        "<p><strong>In-store Pickup:</strong> <span> Unavailable </span></p>"
        "<p><strong>Store Address:</strong> Teststr. 1</p></div></td></tr>"
    )


def _page(rows: str, country: str = "Germany", n: int = 3) -> str:
    return (
        "<html><body><h3>Results for <b>\"80622062\"</b> in "
        f"{n} {country} stores</h3>"
        '<div class="row"><div class="col-5">'
        '<img src="https://www.ikea.com/de/de/images/products/liljebagge__1.jpg" alt="x"></div>'
        '<div class="col-7"><div class="card-body">'
        '<p class="card-title mb-0">LILJEBAGGE Thermostat für Heizkörper, weiß/smart</p>'
        "</div></div></div>"
        "<table><thead><tr><th>Store</th><th>Qty (in store)</th></tr></thead><tbody>"
        f"{rows}</tbody></table></body></html>"
    )


def test_all_zero_and_meta() -> None:
    page = parser.parse_stock_page(_page(_row("Frankfurt", 0) + _row("Wallau", 0)))
    assert page.stores == {"Frankfurt": 0, "Wallau": 0}
    assert page.country_name == "Germany"
    assert page.product_name == "LILJEBAGGE Thermostat für Heizkörper, weiß/smart"


def test_quantities_and_no_confusion() -> None:
    html = _page(_row("Frankfurt", 4) + _row("Walldorf", 9) + _row("Wallau", 12))
    stores = parser.parse_stock_page(html).stores
    assert stores["Frankfurt"] == 4
    assert stores["Wallau"] == 12
    assert stores["Walldorf"] == 9


def test_nbsp_and_missing_closing_tags() -> None:
    html = "<table><tr><td>IKEA&nbsp;Hanau<td>&nbsp;5 </table>"
    assert parser.parse_stock_page(html).stores == {"Hanau": 5}


def test_other_country_heading() -> None:
    page = parser.parse_stock_page(_page(_row("Wien", 1), country="Austria", n=1))
    assert page.country_name == "Austria"


def test_item_not_valid_in_country() -> None:
    html = (
        "<html><body><h3>Fehler</h3><p>\"80622062\" is not a valid product number in IKEA Austria. \n"
        "Try again by either adding dot (###.###.##) or removing all dots (########)</p></body></html>"
    )
    try:
        parser.parse_stock_page(html)
    except parser.ItemNotFoundError as err:
        assert "Austria" in str(err)
        return
    raise AssertionError("ItemNotFoundError erwartet")


def test_structure_change_raises() -> None:
    try:
        parser.parse_stock_page("<html><body>Wartung</body></html>")
    except parser.StockParseError:
        return
    raise AssertionError("StockParseError erwartet")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS ", name)
    print("Alle Tests bestanden.")
