import json
import shutil
from dataclasses import asdict
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from modelle import (
    Bearbeitungsstatus,
    Fallstudie,
    Klausur,
    MehrteiligePruefungsleistung,
    Modul,
    Portfolio,
    Projektpraesentation,
    Pruefungsergebnis,
    Pruefungsleistung,
    Semester,
    Studiengang,
)


PRUEFUNGSARTEN = {
    "Klausur": Klausur,
    "Fallstudie": Fallstudie,
    "Portfolio": Portfolio,
    "Projektpraesentation": Projektpraesentation,
    "Projektpräsentation": Projektpraesentation,
}


def objekt(wert, feld: str) -> dict:
    if not isinstance(wert, dict):
        raise ValueError(f"{feld}: Objekt erwartet.")
    return wert


def liste(wert, feld: str) -> list:
    if not isinstance(wert, list):
        raise ValueError(f"{feld}: Liste erwartet.")
    return wert


def text(wert, feld: str) -> str:
    if not isinstance(wert, str) or not wert.strip():
        raise ValueError(f"{feld}: Text fehlt.")
    return wert.strip()


def ganzzahl(wert, feld: str) -> int:
    if type(wert) is not int or not 1 <= wert <= 2**31 - 1:
        raise ValueError(f"{feld}: Ganze Zahl zwischen 1 und 2147483647 erwartet.")
    return wert


def zahl(wert, feld: str) -> float:
    if type(wert) not in (int, float) or not 0 < wert <= 2**31 - 1:
        raise ValueError(f"{feld}: Positive Zahl bis 2147483647 erwartet.")
    return wert


def datum(wert, feld: str, optional: bool = False) -> date | None:
    if optional and wert is None:
        return None
    if not isinstance(wert, str):
        raise ValueError(f"{feld}: Datum fehlt.")
    try:
        ergebnis = date.fromisoformat(wert)
        if ergebnis.isoformat() != wert:
            raise ValueError
        return ergebnis
    except ValueError:
        raise ValueError(f"{feld}: Datum muss JJJJ-MM-TT entsprechen.") from None


def note(wert) -> float | None:
    if wert is None:
        return None
    wert = zahl(wert, "Note")
    if not 1 <= wert <= 5:
        raise ValueError("Note muss zwischen 1 und 5 liegen.")
    return wert


def pruefung_aus_dict(daten) -> Pruefungsleistung:
    daten = objekt(daten, "Prüfungsleistung")
    art = text(daten.get("klasse"), "Prüfungsart")
    if art not in PRUEFUNGSARTEN:
        raise ValueError(f"Unbekannte Prüfungsart: {art}")
    klasse = PRUEFUNGSARTEN[art]
    ergebnis = daten.get("ergebnis")
    werte = {
        "termin": datum(daten.get("termin"), "Prüfungstermin", optional=True),
        "ergebnis": Pruefungsergebnis(ergebnis) if ergebnis is not None
        else Pruefungsergebnis.AUSSTEHEND,
        "note": note(daten.get("note")),
    }
    if issubclass(klasse, MehrteiligePruefungsleistung):
        anzahl = ganzzahl(daten.get("anzahl_abschnitte"), "Anzahl Abschnitte")
        aktuell = daten.get("aktueller_abschnitt")
        if aktuell is not None:
            aktuell = ganzzahl(aktuell, "Aktueller Abschnitt")
            if aktuell > anzahl:
                raise ValueError("Aktueller Abschnitt ist größer als die Anzahl.")
        werte.update(anzahl_abschnitte=anzahl, aktueller_abschnitt=aktuell)
    return klasse(**werte)


def modul_aus_dict(daten) -> Modul:
    daten = objekt(daten, "Modul")
    return Modul(
        modulcode=text(daten.get("modulcode"), "Modulcode"),
        bezeichnung=text(daten.get("bezeichnung"), "Modulname"),
        ects=zahl(daten.get("ects"), "Modul-ECTS"),
        status=Bearbeitungsstatus(daten.get("status")),
        pruefungsleistung=pruefung_aus_dict(daten.get("pruefungsleistung")),
    )


def semester_aus_dict(daten) -> Semester:
    daten = objekt(daten, "Semester")
    semester = Semester(
        nummer=ganzzahl(daten.get("nummer"), "Semesternummer"),
        module=[modul_aus_dict(m) for m in liste(daten.get("module", []), "Module")],
        beginn=datum(daten.get("beginn"), "Semesterbeginn", optional=True),
        ende=datum(daten.get("ende"), "Semesterende", optional=True),
    )
    if semester.beginn and semester.ende and semester.beginn > semester.ende:
        raise ValueError("Semesterende liegt vor dem Beginn.")
    return semester


def studiengang_aus_dict(daten) -> Studiengang:
    daten = objekt(objekt(daten, "Datei").get("studiengang"), "Studiengang")
    studiengang = Studiengang(
        bezeichnung=text(daten.get("bezeichnung"), "Studiengangname"),
        regelstudienzeit=ganzzahl(daten.get("regelstudienzeit"), "Anzahl Semester"),
        gesamt_ects=ganzzahl(daten.get("gesamt_ects"), "Gesamt-ECTS"),
        enddatum=datum(daten.get("enddatum"), "Enddatum"),
        semester=[
            semester_aus_dict(s)
            for s in liste(daten.get("semester", []), "Semester")
        ],
        zielnote=note(daten.get("zielnote")),
    )
    nummern = [s.nummer for s in studiengang.semester]
    codes = [m.modulcode for m in studiengang.module]
    if len(set(nummern)) != len(nummern) or len(set(codes)) != len(codes):
        raise ValueError("Doppelte Semesternummer oder doppelter Modulcode.")
    return studiengang


def studiengang_als_dict(studiengang: Studiengang) -> dict:
    daten = asdict(studiengang)
    daten["enddatum"] = studiengang.enddatum.isoformat()
    for semester, semester_daten in zip(studiengang.semester, daten["semester"]):
        semester_daten["beginn"] = semester.beginn.isoformat() if semester.beginn else None
        semester_daten["ende"] = semester.ende.isoformat() if semester.ende else None
        for modul, modul_daten in zip(semester.module, semester_daten["module"]):
            pruefung = modul.pruefungsleistung
            pruefungsdaten = modul_daten["pruefungsleistung"]
            pruefungsdaten["klasse"] = type(pruefung).__name__
            pruefungsdaten["termin"] = pruefung.termin.isoformat() if pruefung.termin else None
    return {"studiengang": daten}


def laden(pfad: Path) -> Studiengang:
    with pfad.open(encoding="utf-8-sig") as datei:
        return studiengang_aus_dict(json.load(datei))


def speichern(pfad: Path, studiengang: Studiengang, sichern: bool = False) -> None:
    daten = studiengang_als_dict(studiengang)
    studiengang_aus_dict(daten)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    datei = NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=pfad.parent,
        prefix=".Studiengang-", suffix=".tmp", delete=False,
    )
    temporaer = Path(datei.name)
    try:
        with datei:
            json.dump(daten, datei, ensure_ascii=False, indent=2, allow_nan=False)
            datei.write("\n")
        if sichern and pfad.exists():
            sicherung = pfad.with_name(pfad.name + ".bak")
            nummer = 1
            while sicherung.exists():
                sicherung = pfad.with_name(f"{pfad.name}.{nummer}.bak")
                nummer += 1
            shutil.copy2(pfad, sicherung)
        temporaer.replace(pfad)
    finally:
        temporaer.unlink(missing_ok=True)
