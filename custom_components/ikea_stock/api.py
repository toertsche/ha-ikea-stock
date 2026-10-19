"""Abruf der Bestandsseite. Fester Host, validierte Parameter, Größenlimit."""

from __future__ import annotations

import asyncio
import re

import aiohttp

from .const import BASE_URL, MAX_RESPONSE_BYTES, REQUEST_TIMEOUT, USER_AGENT
from .parser import StockPage, parse_stock_page

_COUNTRY = re.compile(r"^[a-z]{2}$")
_ITEM = re.compile(r"^\d{8}$")


class StockApiError(Exception):
    """Verbindungs- oder HTTP-Fehler."""


async def async_fetch_stock(
    session: aiohttp.ClientSession, country: str, item_no: str
) -> StockPage:
    """Lädt und parst die Seite für Land und Artikelnummer."""
    if not _COUNTRY.match(country) or not _ITEM.match(item_no):
        raise ValueError("Ungültiges Land oder ungültige Artikelnummer")

    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(
                BASE_URL,
                params={"country": country, "itemNo": item_no},
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                allow_redirects=False,
            ) as resp:
                if resp.status != 200:
                    raise StockApiError(f"Unerwarteter HTTP-Status {resp.status}")
                raw = bytearray()
                async for chunk in resp.content.iter_chunked(65536):
                    raw += chunk
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise StockApiError("Antwort zu groß")
    except (aiohttp.ClientError, TimeoutError) as err:
        raise StockApiError(f"Abruf fehlgeschlagen: {err}") from err

    return parse_stock_page(raw.decode("utf-8", errors="replace"))
