import json
import shutil
from dataclasses import asdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import NamedTemporaryFile

from modelle import (
    Bearbeitungsstatus,
    EinteiligePruefungsleistung,
    MehrteiligePruefungsleistung,
    Modul,
    Pruefungsform,
    Pruefungsergebnis,
    Pruefungsleistung,
    Semester,
    Studiengang,
)


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


def note(wert) -> Decimal | None:
    if wert is None:
        return None
    if type(wert) not in (str, int, float, Decimal):
        raise ValueError("Ungültige Note.")
    try:
        ergebnis = Decimal(str(wert))
    except InvalidOperation:
        raise ValueError("Ungültige Note.") from None
    if not ergebnis.is_finite() or not 1 <= ergebnis <= 5:
        raise ValueError("Note muss zwischen 1 und 5 liegen.")
    return ergebnis


def pruefung_aus_dict(daten) -> Pruefungsleistung:
    daten = objekt(daten, "Prüfungsleistung")
    form = Pruefungsform(text(daten.get("pruefungsform"), "Prüfungsform"))
    if form.ist_mehrteilig():
        anzahl = ganzzahl(daten.get("anzahl_abschnitte"), "Anzahl Abschnitte")
        aktuell = daten.get("aktueller_abschnitt")
        if aktuell is not None:
            aktuell = ganzzahl(aktuell, "Aktueller Abschnitt")
            if aktuell > anzahl:
                raise ValueError("Aktueller Abschnitt ist größer als die Anzahl.")
        pruefung = MehrteiligePruefungsleistung(
            pruefungsform=form,
            anzahl_abschnitte=anzahl,
            aktueller_abschnitt=aktuell,
        )
    else:
        if "anzahl_abschnitte" in daten or "aktueller_abschnitt" in daten:
            raise ValueError("Einteilige Prüfungen haben keine Abschnitte.")
        pruefung = EinteiligePruefungsleistung(pruefungsform=form)

    pruefung.termin = datum(daten.get("termin"), "Prüfungstermin", optional=True)
    pruefung.note = note(daten.get("note"))
    if daten.get("ergebnis") is not None:
        pruefung.ergebnis = Pruefungsergebnis(daten["ergebnis"])
    return pruefung


def modul_aus_dict(daten) -> Modul:
    # Hier werden Dateifelder geprüft und bekannte Altzustände angepasst.
    # Die vollständige Modulprüfung über angaben_pruefen() findet hier nicht statt.
    daten = objekt(daten, "Modul")
    modul = Modul(
        modulcode=text(daten.get("modulcode"), "Modulcode"),
        bezeichnung=text(daten.get("bezeichnung"), "Modulname"),
        ects=ganzzahl(daten.get("ects"), "Modul-ECTS"),
        status=Bearbeitungsstatus(daten.get("status")),
        pruefungsleistung=pruefung_aus_dict(daten.get("pruefungsleistung")),
    )
    pruefung = modul.pruefungsleistung
    # Alte Dateien konnten auch Module ohne bestandene Prüfung als fertig führen.
    # Diese werden wieder geöffnet. Bestandene Module in Bearbeitung werden fertig.
    if modul.status == Bearbeitungsstatus.FERTIG and not pruefung.ist_bestanden():
        modul.status = Bearbeitungsstatus.IN_BEARBEITUNG
        if isinstance(pruefung, MehrteiligePruefungsleistung):
            if pruefung.aktueller_abschnitt is None:
                # Bei alten fertigen Modulen ohne Abschnitt nehmen wir den letzten Abschnitt.
                pruefung.aktueller_abschnitt = pruefung.anzahl_abschnitte
    elif modul.status == Bearbeitungsstatus.IN_BEARBEITUNG and pruefung.ist_bestanden():
        modul.status = Bearbeitungsstatus.FERTIG
    if modul.status == Bearbeitungsstatus.FERTIG and isinstance(pruefung, MehrteiligePruefungsleistung):
        pruefung.aktueller_abschnitt = None
    return modul


def semester_aus_dict(daten) -> Semester:
    daten = objekt(daten, "Semester")
    return Semester(
        nummer=ganzzahl(daten.get("nummer"), "Semesternummer"),
        module=[modul_aus_dict(m) for m in liste(daten.get("module", []), "Module")],
    )


def studiengang_aus_dict(daten) -> Studiengang:
    daten = objekt(daten, "Datei")
    daten = objekt(daten.get("studiengang"), "Studiengang")
    studiengang = Studiengang(
        bezeichnung=text(daten.get("bezeichnung"), "Studiengangname"),
        regelstudienzeit=ganzzahl(daten.get("regelstudienzeit"), "Anzahl Semester"),
        gesamt_ects=ganzzahl(daten.get("gesamt_ects"), "Gesamt-ECTS"),
        startdatum=datum(daten.get("startdatum"), "Startdatum"),
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
    daten["startdatum"] = daten["startdatum"].isoformat()
    if daten["zielnote"] is not None:
        daten["zielnote"] = str(daten["zielnote"])
    for semester in daten["semester"]:
        for modul in semester["module"]:
            pruefung = modul["pruefungsleistung"]
            if pruefung["termin"] is not None:
                pruefung["termin"] = pruefung["termin"].isoformat()
            if pruefung["note"] is not None:
                pruefung["note"] = str(pruefung["note"])
    return {"studiengang": daten}


def laden(pfad: Path) -> Studiengang:
    with pfad.open(encoding="utf-8-sig") as datei:
        return studiengang_aus_dict(json.load(datei, parse_float=Decimal))


def speichern(pfad: Path, studiengang: Studiengang, sichern: bool = False) -> None:
    daten = studiengang_als_dict(studiengang)
    # Die Rückumwandlung prüft, ob sich die Daten wieder einlesen lassen.
    # Dabei angepasste Altzustände werden hier nicht in die Schreibdaten übernommen.
    studiengang_aus_dict(daten)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    # Erst die fertige Datei ersetzen, damit bei Fehlern die alten Daten erhalten bleiben.
    datei = NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=pfad.parent,
        prefix=".Studiengang-", suffix=".tmp", delete=False,
    )
    temporaer = Path(datei.name)
    try:
        with datei:
            json.dump(daten, datei, ensure_ascii=False, indent=2, allow_nan=False)
            datei.write("\n")
        # Die Sicherung enthält den Stand vor dem Ersetzen.
        # Die Nummerierung schützt vorhandene Sicherungen vor dem Überschreiben.
        if sichern and pfad.exists():
            sicherung = pfad.with_name(pfad.name + ".bak")
            nummer = 1
            while sicherung.exists():
                sicherung = pfad.with_name(f"{pfad.name}.{nummer}.bak")
                nummer += 1
            shutil.copy2(pfad, sicherung)
        temporaer.replace(pfad)
    finally:
        # Auch bei Fehlern aufräumen. Der Fehler wird an den Aufrufer weitergegeben.
        temporaer.unlink(missing_ok=True)
