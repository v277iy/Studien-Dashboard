from abc import ABC, abstractmethod
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


type Prozent = Decimal


class Bearbeitungsstatus(StrEnum):
    NOCH_ZU_TUN = "NOCH_ZU_TUN"
    IN_BEARBEITUNG = "IN_BEARBEITUNG"
    FERTIG = "FERTIG"


class Pruefungsergebnis(StrEnum):
    AUSSTEHEND = "AUSSTEHEND"
    BESTANDEN = "BESTANDEN"
    NICHT_BESTANDEN = "NICHT_BESTANDEN"


class Pruefungsform(StrEnum):
    KLAUSUR = "Klausur"
    FALLSTUDIE = "Fallstudie"
    PORTFOLIO = "Portfolio"
    PROJEKTPRAESENTATION = "Projektpräsentation"

    def ist_mehrteilig(self) -> bool:
        return self in (Pruefungsform.PORTFOLIO, Pruefungsform.PROJEKTPRAESENTATION)


@dataclass(kw_only=True)
class Pruefungsleistung(ABC):
    pruefungsform: Pruefungsform
    termin: date | None = None
    ergebnis: Pruefungsergebnis = Pruefungsergebnis.AUSSTEHEND
    note: Decimal | None = None

    def __post_init__(self) -> None:
        self.pruefungsform = Pruefungsform(self.pruefungsform)
        if self.note is not None:
            self.note = Decimal(str(self.note))

    @abstractmethod
    def fortschritt(self) -> Prozent:
        pass

    def ist_bestanden(self) -> bool:
        return self.ergebnis == Pruefungsergebnis.BESTANDEN


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
    modulcode: str
    bezeichnung: str
    ects: int
    status: Bearbeitungsstatus
    pruefungsleistung: Pruefungsleistung

    def fortschritt(self) -> Prozent:
        if self.status == Bearbeitungsstatus.NOCH_ZU_TUN:
            return Decimal(0)
        if self.status == Bearbeitungsstatus.FERTIG:
            return Decimal(100)
        return self.pruefungsleistung.fortschritt()

    def angaben_pruefen(self) -> None:
        if type(self.ects) is not int or self.ects < 1:
            raise ValueError("ECTS müssen eine positive ganze Zahl sein.")
        pruefung = self.pruefungsleistung
        if not isinstance(pruefung.pruefungsform, Pruefungsform):
            raise ValueError("Unbekannte Prüfungsform.")
        if pruefung.pruefungsform.ist_mehrteilig() != isinstance(pruefung, MehrteiligePruefungsleistung):
            raise ValueError("Prüfungsform und Gliederung passen nicht zusammen.")
        if self.status not in Bearbeitungsstatus:
            raise ValueError("Unbekannter Bearbeitungsstatus.")
        if pruefung.ergebnis not in Pruefungsergebnis:
            raise ValueError("Unbekanntes Prüfungsergebnis.")
        if self.status != Bearbeitungsstatus.FERTIG:
            if pruefung.note is not None or pruefung.ergebnis != Pruefungsergebnis.AUSSTEHEND:
                raise ValueError("Ergebnis und Note sind erst nach Abschluss möglich.")
        if pruefung.note is not None:
            if (
                not isinstance(pruefung.note, Decimal)
                or not pruefung.note.is_finite()
                or not 1 <= pruefung.note <= 5
            ):
                raise ValueError("Note muss zwischen 1 und 5 liegen.")
            if pruefung.ergebnis == Pruefungsergebnis.AUSSTEHEND:
                raise ValueError("Für eine Note muss das Ergebnis feststehen.")
            bestanden = pruefung.ergebnis == Pruefungsergebnis.BESTANDEN
            if bestanden != (pruefung.note <= 4):
                raise ValueError("Note und Prüfungsergebnis passen nicht zusammen.")
        if isinstance(pruefung, MehrteiligePruefungsleistung):
            anzahl = pruefung.anzahl_abschnitte
            aktuell = pruefung.aktueller_abschnitt
            if type(anzahl) is not int or anzahl < 1:
                raise ValueError("Die Abschnittszahl muss positiv sein.")
            if self.status == Bearbeitungsstatus.IN_BEARBEITUNG:
                if type(aktuell) is not int or not 1 <= aktuell <= anzahl:
                    raise ValueError("Der aktuelle Abschnitt liegt außerhalb des Bereichs.")
            elif aktuell is not None:
                raise ValueError("Ein aktueller Abschnitt ist nur in Bearbeitung möglich.")


@dataclass
class Semester:
    nummer: int
    module: list[Modul] = field(default_factory=list)

    def ist_fertig(self) -> bool:
        return bool(self.module) and all(
            modul.status == Bearbeitungsstatus.FERTIG for modul in self.module
        )


@dataclass
class Studiengang:
    bezeichnung: str
    regelstudienzeit: int
    gesamt_ects: int
    startdatum: date
    semester: list[Semester] = field(default_factory=list)
    zielnote: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.startdatum, date):
            raise ValueError("Ein gültiges Startdatum ist erforderlich.")
        if type(self.regelstudienzeit) is not int or self.regelstudienzeit < 1:
            raise ValueError("Die Semesterzahl muss eine positive ganze Zahl sein.")
        if self.startdatum.year + (self.startdatum.month - 1 + 6 * self.regelstudienzeit) // 12 > 9999:
            raise ValueError("Das berechnete Enddatum liegt nach dem Jahr 9999.")
        if self.zielnote is not None:
            self.zielnote = Decimal(str(self.zielnote))

    @property
    def enddatum(self) -> date:
        monate = self.startdatum.month - 1 + 6 * self.regelstudienzeit
        jahr = self.startdatum.year + monate // 12
        monat = monate % 12 + 1
        tag = min(self.startdatum.day, monthrange(jahr, monat)[1])
        return date(jahr, monat, tag)

    def verbleibende_tage(self, heute: date | None = None) -> int:
        return (self.enddatum - (heute or date.today())).days

    @property
    def module(self) -> list[Modul]:
        return [modul for semester in self.semester for modul in semester.module]

    def aktuelles_semester(self) -> int | None:
        return min((
            semester.nummer for semester in self.semester
            if any(modul.status != Bearbeitungsstatus.FERTIG for modul in semester.module)
        ), default=None)

    def verbleibende_semester(self) -> int:
        zusaetzlich = {s.nummer for s in self.semester if s.nummer > self.regelstudienzeit}
        fertig = {s.nummer for s in self.semester if s.ist_fertig()}
        return max(0, self.regelstudienzeit + len(zusaetzlich) - len(fertig))

    def modul_hinzufuegen(self, modul: Modul, semesternummer: int) -> None:
        if type(semesternummer) is not int or not 1 <= semesternummer <= self.regelstudienzeit:
            raise ValueError(f"Semester muss zwischen 1 und {self.regelstudienzeit} liegen.")
        if any(m.modulcode == modul.modulcode for m in self.module):
            raise ValueError("Dieser Modulcode ist bereits vergeben.")
        modul.angaben_pruefen()
        semester = next((s for s in self.semester if s.nummer == semesternummer), None)
        if semester is None:
            semester = Semester(semesternummer)
            self.semester.append(semester)
        semester.module.append(modul)

    def modul_finden(self, modulcode: str) -> tuple[Semester, Modul]:
        for semester in self.semester:
            for modul in semester.module:
                if modul.modulcode == modulcode:
                    return semester, modul
        raise ValueError("Modul wurde nicht gefunden.")

    def modul_aktualisieren(
        self, alter_code: str, modul: Modul, semesternummer: int
    ) -> None:
        altes_semester, altes_modul = self.modul_finden(alter_code)
        if type(semesternummer) is not int or not (
            1 <= semesternummer <= self.regelstudienzeit
            or semesternummer == altes_semester.nummer
        ):
            raise ValueError(f"Semester muss zwischen 1 und {self.regelstudienzeit} liegen.")
        if any(m is not altes_modul and m.modulcode == modul.modulcode for m in self.module):
            raise ValueError("Dieser Modulcode ist bereits vergeben.")
        modul.angaben_pruefen()
        if semesternummer == altes_semester.nummer:
            index = altes_semester.module.index(altes_modul)
            altes_semester.module[index] = modul
        else:
            ziel = next((s for s in self.semester if s.nummer == semesternummer), None)
            if ziel is None:
                ziel = Semester(semesternummer)
                self.semester.append(ziel)
            altes_semester.module.remove(altes_modul)
            ziel.module.append(modul)

    def erreichte_ects(self) -> int:
        return sum(m.ects for m in self.module if m.pruefungsleistung.ist_bestanden())

    def ects_fortschritt(self) -> Prozent:
        return Decimal(100) * self.erreichte_ects() / self.gesamt_ects

    def notendurchschnitt(self) -> Decimal | None:
        benotet = [
            m for m in self.module
            if m.pruefungsleistung.ist_bestanden() and m.pruefungsleistung.note is not None
        ]
        ects = sum(m.ects for m in benotet)
        if not ects:
            return None
        notensumme = sum((
            m.ects * m.pruefungsleistung.note for m in benotet
        ), Decimal(0))
        return notensumme / ects

    def zielnote_erreicht(self) -> bool | None:
        durchschnitt = self.notendurchschnitt()
        if durchschnitt is None or self.zielnote is None:
            return None
        return durchschnitt <= self.zielnote
