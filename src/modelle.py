from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Bearbeitungsstatus(StrEnum):
    NOCH_ZU_TUN = "NOCH_ZU_TUN"
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    FERTIG = "FERTIG"


class Pruefungsergebnis(StrEnum):
    AUSSTEHEND = "AUSSTEHEND"
    BESTANDEN = "BESTANDEN"
    NICHT_BESTANDEN = "NICHT_BESTANDEN"


@dataclass(kw_only=True)
class Pruefungsleistung(ABC):
    termin: date | None = None
    ergebnis: Pruefungsergebnis = Pruefungsergebnis.AUSSTEHEND
    note: float | None = None

    @abstractmethod
    def fortschritt(self) -> float:
        pass

    def ist_bestanden(self) -> bool:
        return self.ergebnis == Pruefungsergebnis.BESTANDEN


class EinteiligePruefungsleistung(Pruefungsleistung):
    def fortschritt(self) -> float:
        return 0.0


@dataclass
class MehrteiligePruefungsleistung(Pruefungsleistung):
    anzahl_abschnitte: int
    aktueller_abschnitt: int | None = None

    def fortschritt(self) -> float:
        return 100 * (self.aktueller_abschnitt or 0) / self.anzahl_abschnitte


class Klausur(EinteiligePruefungsleistung):
    pass


class Fallstudie(EinteiligePruefungsleistung):
    pass


class Portfolio(MehrteiligePruefungsleistung):
    pass


class Projektpraesentation(MehrteiligePruefungsleistung):
    pass


@dataclass
class Modul:
    modulcode: str
    bezeichnung: str
    ects: float
    status: Bearbeitungsstatus
    pruefungsleistung: Pruefungsleistung

    def fortschritt(self) -> float:
        if self.status == Bearbeitungsstatus.NOCH_ZU_TUN:
            return 0.0
        if self.status == Bearbeitungsstatus.FERTIG:
            return 100.0
        return self.pruefungsleistung.fortschritt()


@dataclass
class Semester:
    nummer: int
    module: list[Modul] = field(default_factory=list)
    beginn: date | None = None
    ende: date | None = None


@dataclass
class Studiengang:
    bezeichnung: str
    regelstudienzeit: int
    gesamt_ects: int
    enddatum: date
    semester: list[Semester] = field(default_factory=list)
    zielnote: float | None = None

    @property
    def module(self) -> list[Modul]:
        return [modul for semester in self.semester for modul in semester.module]

    def modul_hinzufuegen(self, modul: Modul, semesternummer: int) -> None:
        if type(semesternummer) is not int or not 1 <= semesternummer <= self.regelstudienzeit:
            raise ValueError(f"Semester muss zwischen 1 und {self.regelstudienzeit} liegen.")
        if any(m.modulcode == modul.modulcode for m in self.module):
            raise ValueError("Dieser Modulcode ist bereits vergeben.")
        semester = next((s for s in self.semester if s.nummer == semesternummer), None)
        if semester is None:
            semester = Semester(semesternummer)
            self.semester.append(semester)
        semester.module.append(modul)

    def erreichte_ects(self) -> float:
        return sum(m.ects for m in self.module if m.pruefungsleistung.ist_bestanden())

    def ects_fortschritt(self) -> float:
        return 100 * self.erreichte_ects() / self.gesamt_ects

    def notendurchschnitt(self) -> float | None:
        benotet = [
            m for m in self.module
            if m.pruefungsleistung.ist_bestanden() and m.pruefungsleistung.note is not None
        ]
        ects = sum(m.ects for m in benotet)
        if not ects:
            return None
        return sum(m.ects * m.pruefungsleistung.note for m in benotet) / ects
