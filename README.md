# IKEA Stock Watch (Home Assistant / HACS)

Überwacht die Filialbestände (Qty) eines IKEA-Artikels über [easyrebuild.com/stock](https://easyrebuild.com/stock) und meldet, sobald ein gewählter Markt von 0 auf > 0 springt.

## Installation (HACS)

1. HACS → ⋮ → *Benutzerdefinierte Repositories* → https://https://github.com/toertsche/ha-ikea-stock, Kategorie *Integration*.
2. Installieren, Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → IKEA Stock Watch*.

## Einrichtung

1. **Land + Artikelnummer** (8 Ziffern, Punkte werden ignoriert). Die Eingabe wird live gegen die Seite geprüft.
2. **Märkte** (Mehrfachauswahl, Liste kommt aus der Seite), **Prüfintervall** (min. 10 Min, Standard 30), optional **notify-Entität** und persistente Benachrichtigung.
3. Später änderbar über *Konfigurieren* an der Integration. Weitere Artikel = weitere Instanz hinzufügen.

## Entitäten (pro Artikel ein Gerät, pro Markt zwei Entitäten)

| Entität | Bedeutung |
|---|---|
| `sensor.<markt>_bestand` | Qty im Markt |
| `binary_sensor.<markt>_verfuegbar` | an, wenn Qty > 0 |

## Benachrichtigung auf HA-üblichen Wegen

- Optional direkt in der Integration: `notify`-Entität (Companion-App, E-Mail …) und/oder persistente Benachrichtigung.
- Event `ikea_stock_available` (Felder: `store`, `quantity`, `item_no`, `product_name`, `country`, `entry_id`) bei jedem Wechsel 0 → > 0.
- Beim Einrichten wird nur der Ausgangsstand gespeichert, kein Alarm für bereits vorhandenen Bestand.

Beispiel-Automation (eigene Logik, z. B. Sprachausgabe):

```yaml
triggers:
  - trigger: event
    event_type: ikea_stock_available
actions:
  - action: notify.mobile_app_dein_handy
    data:
      title: "IKEA verfügbar"
      message: "{{ trigger.event.data.product_name }} – {{ trigger.event.data.store }}: {{ trigger.event.data.quantity }}"
```

## Hinweise / Grenzen

- Inoffizielle Drittquelle ohne API-Zusage. Ändert sich die Seite, werden die Entitäten `nicht verfügbar` (Parser: `parser.py`).
- **Länder:** Die Auswahl entspricht exakt dem Länder-Dropdown der Seite (`country=<code>`). Ist ein Artikel in einem Land nicht gelistet (z. B. 80622062 in Österreich), meldet die Seite „not a valid product number" – die Einrichtung zeigt dann eine passende Fehlermeldung. Länderformate der Artikelnummer (z. B. mit Punkten) werden auf 8 Ziffern normalisiert; Länder mit abweichendem Nummernformat sind nicht getestet.
- Struktur der Seite zuletzt am 19.10.2026 im Browser gegen das echte HTML geprüft (Deutschland).
- Ein Request pro Intervall und Artikel für alle Märkte; Mindestintervall 10 Minuten.
- Gespeichert wird nur der letzte Mengenstand (HA-Storage), beim Entfernen der Integration gelöscht.
- Bestandsdaten sind Momentaufnahmen und können vom Ist-Bestand abweichen.

## Tests

`python tests/test_parser.py` (Parser, ohne Home Assistant).

## Changelog

- 1.0.0 Erstversion
