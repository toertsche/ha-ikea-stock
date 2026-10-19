"""HTML-Parser für die easyrebuild.com-Bestandsseite (nur Standardbibliothek)."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re

_WS = re.compile(r"[\s ]+")
_HEADING = re.compile(r"\bin\s+(\d+)\s+(.+?)\s+stores\b", re.IGNORECASE)
_STORE = re.compile(r"^IKEA\s+(.+)$", re.IGNORECASE)
_QTY = re.compile(r"^\d{1,6}$")


_NOT_VALID = re.compile(r"is not a valid product number in IKEA\s+(.+?)\s*\.", re.IGNORECASE)


class StockParseError(Exception):
    """Seite enthält keine erkennbare Bestandstabelle."""


class ItemNotFoundError(StockParseError):
    """Die Seite meldet: Artikelnummer ist in diesem Land nicht gültig/gelistet."""


@dataclass(frozen=True)
class StockPage:
    """Ergebnis einer Abfrage."""

    product_name: str | None
    country_name: str | None
    stores: dict[str, int] = field(default_factory=dict)


def _clean(text: str) -> str:
    return _WS.sub(" ", text).strip()


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.text: list[str] = []
        self.product_name: str | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._expect_name = False

    def _close_cell(self) -> None:
        if self._cell is not None and self._row is not None:
            self._row.append(_clean("".join(self._cell)))
        self._cell = None

    def _close_row(self) -> None:
        self._close_cell()
        if self._row:
            self.rows.append(self._row)
        self._row = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._close_row()
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._close_cell()
            self._cell = []
        elif tag == "br":
            if self._cell is not None:
                self._cell.append(" ")
            self.text.append(" ")
        elif tag == "img":
            src = dict(attrs).get("src") or ""
            if "/images/products/" in src and self.product_name is None:
                self._expect_name = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._close_cell()
        elif tag == "tr":
            self._close_row()

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._cell is not None:
            self._cell.append(data)
        elif self._expect_name and data.strip():
            self.product_name = _clean(data)
            self._expect_name = False


def parse_stock_page(html: str) -> StockPage:
    """Liest Stores und Qty aus der Seite. Wirft StockParseError ohne Treffer."""
    collector = _Collector()
    collector.feed(html)
    collector.close()
    collector._close_row()  # noqa: SLF001 - offene Zeile am Dokumentende

    stores: dict[str, int] = {}
    for cells in collector.rows:
        if len(cells) < 2:
            continue
        match = _STORE.match(cells[0])
        if match and _QTY.match(cells[1]):
            stores[match.group(1).strip()] = int(cells[1])

    full_text = _clean(" ".join(collector.text))
    if not stores:
        if match := _NOT_VALID.search(full_text):
            raise ItemNotFoundError(f"Artikelnummer in IKEA {match.group(1)} nicht gültig")
        raise StockParseError("Keine Store-Zeilen gefunden (Seitenstruktur geändert?)")

    heading = _HEADING.search(full_text)
    return StockPage(
        product_name=collector.product_name,
        country_name=heading.group(2) if heading else None,
        stores=stores,
    )
