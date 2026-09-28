import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory


class Bearbeitungsstatus(Enum):
    NOCH_ZU_TUN = "NOCH_ZU_TUN"
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    FERTIG = "FERTIG"


class Pruefungsergebnis(Enum):
    AUSSTEHEND = "AUSSTEHEND"
    BESTANDEN = "BESTANDEN"
    NICHT_BESTANDEN = "NICHT_BESTANDEN"


class Pruefungsform(Enum):
    KLAUSUR = "Klausur"
    FALLSTUDIE = "Fallstudie"
    PORTFOLIO = "Portfolio"
    PROJEKTPRAESENTATION = "Projektpräsentation"


@dataclass
class Pruefungsdaten:
    status: Bearbeitungsstatus
    form: Pruefungsform
    note: Decimal
    termin: date
    ergebnis: Pruefungsergebnis


def main():
    original = Pruefungsdaten(
        Bearbeitungsstatus.FERTIG, Pruefungsform.PORTFOLIO,
        Decimal("1.7"), date(2027, 3, 1), Pruefungsergebnis.BESTANDEN,
    )
    daten = {
        "status": original.status.value,
        "form": original.form.value,
        "note": str(original.note),
        "termin": original.termin.isoformat(),
        "ergebnis": original.ergebnis.value,
    }

    # Die Testdatei wird danach automatisch gelöscht.
    with TemporaryDirectory() as ordner:
        pfad = Path(ordner) / "pruefung.json"
        with open(pfad, "w", encoding="utf-8") as datei:
            json.dump(daten, datei)
        with open(pfad, encoding="utf-8") as datei:
            gelesen = json.load(datei)

    geladen = Pruefungsdaten(
        Bearbeitungsstatus(gelesen["status"]),
        Pruefungsform(gelesen["form"]),
        Decimal(gelesen["note"]),
        date.fromisoformat(gelesen["termin"]),
        Pruefungsergebnis(gelesen["ergebnis"]),
    )
    assert geladen == original
    print("T4: Datum, Decimal und Enums werden in JSON gespeichert und wiederhergestellt.")


if __name__ == "__main__":
    main()
