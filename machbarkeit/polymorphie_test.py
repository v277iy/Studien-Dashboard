"""Machbarkeitstest für polymorphe Fortschrittsberechnungen."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class Bearbeitungsstatus(Enum):
    NOCH_ZU_TUN = "NOCH_ZU_TUN"
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    FERTIG = "FERTIG"




class Pruefungsleistung(ABC):
    @abstractmethod
    def fortschritt(self) -> float:
        """Gibt den Zwischenstand anhand der Gliederung der Leistung zurück."""


@dataclass
class EinteiligePruefungsleistung(Pruefungsleistung):
    def fortschritt(self) -> float:
        # Eine einteilige Leistung besitzt keine einzelnen Bearbeitungsabschnitte.
        return 0.0


class Klausur(EinteiligePruefungsleistung):
    pass




@dataclass
class MehrteiligePruefungsleistung(Pruefungsleistung):
    anzahl_abschnitte: int
    aktueller_abschnitt: int | None = None

    def __post_init__(self) -> None:
        if self.anzahl_abschnitte < 1:
            raise ValueError("Die Anzahl der Abschnitte muss positiv sein.")
        if (
            self.aktueller_abschnitt is not None
            and not 1 <= self.aktueller_abschnitt <= self.anzahl_abschnitte
        ):
            raise ValueError("Der aktuelle Abschnitt liegt außerhalb des gültigen Bereichs.")

    def fortschritt(self) -> float:
        if self.aktueller_abschnitt is None:
            raise ValueError("Während der Bearbeitung muss ein Abschnitt gesetzt sein.")
        return 100.0 * self.aktueller_abschnitt / self.anzahl_abschnitte


class Fallstudie(EinteiligePruefungsleistung):
    pass


class Portfolio(MehrteiligePruefungsleistung):
    pass


class Projektpräsentation(MehrteiligePruefungsleistung):
    pass


@dataclass
class Modul:
    status: Bearbeitungsstatus
    pruefungsleistung: Pruefungsleistung

    def fortschritt(self) -> float:
        if self.status is Bearbeitungsstatus.NOCH_ZU_TUN:
            return 0.0
        if self.status is Bearbeitungsstatus.FERTIG:
            return 100.0
        return self.pruefungsleistung.fortschritt()


def main() -> None:
    module = [
        Modul(Bearbeitungsstatus.IN_BEARBEITUNG, Klausur()),
        Modul(
            Bearbeitungsstatus.IN_BEARBEITUNG,
            Fallstudie(),
        ),
        Modul(
            Bearbeitungsstatus.IN_BEARBEITUNG,
            Portfolio(anzahl_abschnitte=4, aktueller_abschnitt=2),
        ),
        Modul(
            Bearbeitungsstatus.NOCH_ZU_TUN,
            Projektpräsentation(anzahl_abschnitte=4),
        ),
        Modul(
            Bearbeitungsstatus.FERTIG,
            Portfolio(anzahl_abschnitte=4),
        ),
    ]
    fortschritte = [modul.fortschritt() for modul in module]
    pruefungsformen = [
        type(modul.pruefungsleistung).__name__ for modul in module
    ]
    assert fortschritte == [0.0, 0.0, 50.0, 0.0, 100.0]
    assert pruefungsformen == [
        "Klausur",
        "Fallstudie",
        "Portfolio",
        "Projektpräsentation",
        "Portfolio",
    ]
    print(f"Polymorpher Aufruf erfolgreich: {fortschritte}")
    print(f"Aus Klassennamen ermittelte Prüfungsformen: {pruefungsformen}")


if __name__ == "__main__":
    main()
