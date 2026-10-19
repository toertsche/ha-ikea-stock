"""Konstanten für IKEA Stock Watch."""

from __future__ import annotations

DOMAIN = "ikea_stock"

BASE_URL = "https://easyrebuild.com/stock"
USER_AGENT = "HomeAssistant-ikea_stock/1.0 (privater Gebrauch)"
REQUEST_TIMEOUT = 20
MAX_RESPONSE_BYTES = 2_000_000

CONF_COUNTRY = "country"
CONF_ITEM_NO = "item_no"
CONF_STORES = "stores"
CONF_SCAN_INTERVAL = "scan_interval"  # Minuten
CONF_NOTIFY_ENTITY = "notify_entity"
CONF_PERSISTENT = "persistent_notification"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10  # schont die Fremdseite
MAX_SCAN_INTERVAL = 1440

EVENT_AVAILABLE = f"{DOMAIN}_available"

# Anzeigenamen und Codes exakt wie im <select name="country"> auf easyrebuild.com/stock.
# Der Config-Flow prüft zusätzlich das Land in der Ergebnisüberschrift.
COUNTRIES: dict[str, str] = {
    "de": "Germany",
    "at": "Austria",
    "be": "Belgium",
    "hr": "Croatia",
    "cz": "Czech Republic",
    "dk": "Denmark",
    "fi": "Finland",
    "fr": "France",
    "hu": "Hungary",
    "ie": "Ireland",
    "it": "Italy",
    "nl": "Netherlands",
    "no": "Norway",
    "pl": "Poland",
    "pt": "Portugal",
    "ro": "Romania",
    "rs": "Serbia",
    "sk": "Slovakia",
    "si": "Slovenia",
    "es": "Spain",
    "se": "Sweden",
    "ch": "Switzerland",
    "gb": "United Kingdom",
    "us": "USA",
    "ca": "Canada",
    "mx": "Mexico",
    "co": "Colombia",
    "in": "India",
    "il": "Israel",
    "jp": "Japan",
    "kr": "Korea",
    "my": "Malaysia",
    "ph": "Philippines",
    "sa": "Saudi Arabia",
    "sg": "Singapore",
    "th": "Thailand",
    "ae": "United Arab Emirates",
    "ma": "Morocco",
    "au": "Australia",
    "nz": "New Zealand",
}


def storage_key(entry_id: str) -> str:
    """Schlüssel für den persistierten Letztstand."""
    return f"{DOMAIN}.{entry_id}"
