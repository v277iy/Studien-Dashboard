"""Kleiner Machbarkeitstest für die Speicherung der Dashboard-Daten in JSON."""

from __future__ import annotations

import json
from pathlib import Path

DATEIPFAD = Path(__file__).with_name("testdaten.json")

TESTDATEN = {
    "studiengang": {
        "bezeichnung": "B.Sc. Informatik",
        "startdatum": "2026-10-01",
        "regelstudienzeit": 6,
        "gesamt_ects": 180,
        "zielnote": 2.0,
        "semester": [
            {
                "nummer": 3,
                "module": [
                    {
                        "modulcode": "OOP-PY",
                        "bezeichnung": "OOP mit Python",
                        "ects": 5,
                        "status": "IN_BEARBEITUNG",
                        "pruefungsleistung": {
                            "pruefungsform": "Portfolio",
                            "ergebnis": None,
                            "note": None,
                            "anzahl_abschnitte": 4,
                            "aktueller_abschnitt": 2,
                        },
                    }
                ],
            }
        ],
    }
}


def main() -> None:
    with DATEIPFAD.open("w", encoding="utf-8") as datei:
        json.dump(TESTDATEN, datei, ensure_ascii=False, indent=2)

    with DATEIPFAD.open("r", encoding="utf-8") as datei:
        geladene_daten = json.load(datei)

    assert geladene_daten == TESTDATEN
    print(f"JSON-Rundlauf erfolgreich: {DATEIPFAD}")


if __name__ == "__main__":
    main()
