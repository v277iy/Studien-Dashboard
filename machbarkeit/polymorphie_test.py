from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


type Prozent = Decimal


class Bearbeitungsstatus(StrEnum):
    NOCH_ZU_TUN = "NOCH_ZU_TUN"
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    FERTIG = "FERTIG"


class Pruefungsform(StrEnum):
    KLAUSUR = "Klausur"
    FALLSTUDIE = "Fallstudie"
    PORTFOLIO = "Portfolio"
    PROJEKTPRAESENTATION = "Projektpräsentation"


@dataclass(kw_only=True)
class Pruefungsleistung(ABC):
    pruefungsform: Pruefungsform

    @abstractmethod
    def fortschritt(self) -> Prozent:
        pass


class EinteiligePruefungsleistung(Pruefungsleistung):
    def fortschritt(self) -> Prozent:
        return Decimal(0)


@dataclass
class MehrteiligePruefungsleistung(Pruefungsleistung):
    anzahl_abschnitte: int
    aktueller_abschnitt: int | None = None

    def fortschritt(self) -> Prozent:
        return Decimal(100) * (self.aktueller_abschnitt or 0) / self.anzahl_abschnitte


@dataclass
class Modul:
    status: Bearbeitungsstatus
    pruefungsleistung: Pruefungsleistung

    def fortschritt(self) -> Prozent:
        if self.status == Bearbeitungsstatus.NOCH_ZU_TUN:
            return Decimal(0)
        if self.status == Bearbeitungsstatus.FERTIG:
            return Decimal(100)
        return self.pruefungsleistung.fortschritt()


def main() -> None:
    module = [
        Modul(Bearbeitungsstatus.IN_BEARBEITUNG, EinteiligePruefungsleistung(pruefungsform=Pruefungsform.KLAUSUR)),
        Modul(Bearbeitungsstatus.IN_BEARBEITUNG, EinteiligePruefungsleistung(pruefungsform=Pruefungsform.FALLSTUDIE)),
        Modul(Bearbeitungsstatus.IN_BEARBEITUNG, MehrteiligePruefungsleistung(4, 2, pruefungsform=Pruefungsform.PORTFOLIO)),
        Modul(Bearbeitungsstatus.NOCH_ZU_TUN, MehrteiligePruefungsleistung(4, pruefungsform=Pruefungsform.PROJEKTPRAESENTATION)),
        Modul(Bearbeitungsstatus.FERTIG, MehrteiligePruefungsleistung(4, pruefungsform=Pruefungsform.PORTFOLIO)),
    ]
    fortschritte = [m.fortschritt() for m in module]
    assert fortschritte == [0, 0, 50, 0, 100]
    assert all(isinstance(wert, Decimal) for wert in fortschritte)
    assert len({type(m.pruefungsleistung) for m in module}) == 2
    print(f"Polymorpher Aufruf erfolgreich: {fortschritte}")
    print([m.pruefungsleistung.pruefungsform.value for m in module])


if __name__ == "__main__":
    main()
