from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from modelle import (
    Bearbeitungsstatus,
    MehrteiligePruefungsleistung,
    Modul,
    Pruefungsergebnis,
    Studiengang,
)


def dezimal(wert: float | None) -> str:
    return "—" if wert is None else f"{wert:.1f}".replace(".", ",")


def label(text: str, rolle: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setProperty("rolle", rolle)
    return widget


def balken(wert: float = 0) -> QProgressBar:
    widget = QProgressBar()
    widget.setRange(0, 100)
    widget.setValue(round(min(100, max(0, wert))))
    widget.setTextVisible(False)
    widget.setFixedHeight(9)
    return widget


def kennzahlenkasten(
    titel: str, links: QVBoxLayout, rechts: QVBoxLayout
) -> QFrame:
    kasten = QFrame()
    kasten.setObjectName("kennzahlen")
    kasten.setFixedHeight(126)

    layout = QGridLayout(kasten)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setHorizontalSpacing(24)
    layout.setVerticalSpacing(8)
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(2, 1)
    layout.addWidget(label(titel, "titel"), 0, 0)
    layout.addLayout(links, 1, 0)
    layout.addLayout(rechts, 1, 2)

    trenner = QFrame()
    trenner.setObjectName("trenner")
    trenner.setFixedWidth(1)
    layout.addWidget(trenner, 0, 1, 2, 1)
    return kasten


def studienfortschritt(studiengang: Studiengang) -> QFrame:
    links = QVBoxLayout()
    links.setSpacing(4)
    links.addWidget(label("Erreichte ECTS", "muted"))
    erreicht = studiengang.erreichte_ects()
    prozent = studiengang.ects_fortschritt()
    links.addWidget(label(f"{erreicht:g} / {studiengang.gesamt_ects}", "wert"))
    fortschritt = QHBoxLayout()
    fortschritt.addWidget(balken(prozent), 1)
    fortschritt.addWidget(label(f"{prozent:.0f} %", "klein"))
    links.addLayout(fortschritt)

    rechts = QVBoxLayout()
    rechts.setSpacing(4)
    rechts.addWidget(label("Aktuelle Durchschnittsnote", "muted"))
    noten = QHBoxLayout()
    noten.addWidget(label(dezimal(studiengang.notendurchschnitt()), "wert"))
    if studiengang.zielnote is not None:
        ziel = label(f"Ziel: {dezimal(studiengang.zielnote)}", "ziel")
        ziel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ziel.setFixedHeight(23)
        noten.addWidget(ziel)
    noten.addStretch()
    rechts.addLayout(noten)
    offen = max(0, studiengang.gesamt_ects - erreicht)
    rechts.addWidget(label(f"{offen:g} ECTS noch offen", "klein"))
    return kennzahlenkasten("Studienfortschritt", links, rechts)


def zeitplan(studiengang: Studiengang) -> QFrame:
    heute = date.today()
    aktuell = next((
        s.nummer for s in studiengang.semester
        if s.beginn and s.ende and s.beginn <= heute <= s.ende
    ), None)
    semestertext = (
        f"Aktuelles Semester: {aktuell}" if aktuell is not None
        else f"Semester insgesamt: {studiengang.regelstudienzeit}"
    )
    tage = (studiengang.enddatum - heute).days
    restzeit = f"Noch {tage} Tage" if tage > 0 else f"Vor {-tage} Tagen"
    if tage == 0:
        restzeit = "Enddatum heute"
    spalten = []
    for titel, datum, zusatz in (
        ("Aktuelles Datum", heute, semestertext),
        ("Geplantes Enddatum", studiengang.enddatum, restzeit),
    ):
        spalte = QVBoxLayout()
        spalte.setSpacing(4)
        spalte.addWidget(label(titel, "muted"))
        spalte.addWidget(label(datum.strftime("%d.%m.%Y"), "wert"))
        spalte.addWidget(label(zusatz, "klein"))
        spalten.append(spalte)
    return kennzahlenkasten("Zeitplan", spalten[0], spalten[1])


def modulkarte(modul: Modul, status: str) -> QFrame:
    karte = QFrame()
    karte.setObjectName("modulkarte")
    karte.setProperty("status", status)
    karte.setToolTip(modul.modulcode)
    pruefung = modul.pruefungsleistung
    mehrteilig = isinstance(pruefung, MehrteiligePruefungsleistung) and status != "fertig"
    karte.setMinimumHeight(150 if mehrteilig else 110)
    karte.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    schatten = QGraphicsDropShadowEffect(karte)
    schatten.setBlurRadius(12)
    schatten.setOffset(0, 3)
    schatten.setColor(QColor(23, 32, 51, 32))
    karte.setGraphicsEffect(schatten)

    layout = QVBoxLayout(karte)
    layout.setContentsMargins(14, 12, 18, 18)
    layout.setSpacing(6)
    titel = label(modul.bezeichnung, "titel")
    titel.setWordWrap(True)
    titel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    layout.addWidget(titel)
    pruefungsart = type(pruefung).__name__.replace("Projektpraesentation", "Projektpräsentation")
    layout.addWidget(label(f"{pruefungsart} · {modul.ects:g} ECTS", "muted"))

    if mehrteilig:
        abschnitt = pruefung.aktueller_abschnitt or "—"
        layout.addWidget(label(
            f"Aktueller Abschnitt: {abschnitt} von {pruefung.anzahl_abschnitte}", "klein"
        ))
        fortschritt = balken(modul.fortschritt())
        fortschritt.setProperty("status", status)
        layout.addWidget(fortschritt)
        prozent = label(f"{modul.fortschritt():.0f} %", "prozent")
        prozent.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(prozent)

    layout.addSpacing(4)
    unten = QHBoxLayout()
    statustext = {
        "offen": "NICHT BEGONNEN",
        "aktiv": "IN BEARBEITUNG",
        "fertig": "ABGESCHLOSSEN",
    }[status]
    if pruefung.ergebnis != Pruefungsergebnis.AUSSTEHEND:
        statustext = pruefung.ergebnis.replace("_", " ")
    badge = label(statustext, "status")
    badge.setProperty("status", status)
    badge.setProperty("ergebnis", pruefung.ergebnis.value)
    badge.setFixedHeight(23)
    unten.addWidget(badge)
    unten.addStretch()
    if pruefung.note is not None:
        unten.addWidget(label(f"Note: {dezimal(pruefung.note)}", "note"))
    elif pruefung.termin is not None:
        termin = label(pruefung.termin.strftime("%d.%m.%Y"), "klein")
        termin.setToolTip("Prüfungstermin")
        unten.addWidget(termin)
    layout.addLayout(unten)
    layout.addStretch()
    return karte


def kanbanspalte(titel: str, status: str, module: list[Modul]) -> QWidget:
    spalte = QWidget()
    spalte.setObjectName("kanbanspalte")
    spalte.setMinimumWidth(300)
    layout = QVBoxLayout(spalte)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    kopf = QFrame()
    kopf.setObjectName("spaltenkopf")
    kopf.setProperty("status", status)
    kopf.setFixedHeight(48)
    kopf_layout = QHBoxLayout(kopf)
    kopf_layout.setContentsMargins(17, 0, 17, 0)
    kopf_layout.setSpacing(10)
    punkt = label("", "punkt")
    punkt.setProperty("status", status)
    punkt.setFixedSize(14, 14)
    kopf_layout.addWidget(punkt)
    kopf_layout.addWidget(label(titel, "titel"))
    kopf_layout.addStretch()
    anzahl = label(str(len(module)), "anzahl")
    anzahl.setFixedHeight(23)
    anzahl.setMinimumWidth(25)
    anzahl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    kopf_layout.addWidget(anzahl)
    layout.addWidget(kopf)

    for modul in module:
        layout.addWidget(modulkarte(modul, status))
    if not module:
        leer = label("Keine Module", "muted")
        leer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(leer)
    layout.addStretch()
    return spalte


def kanbanboard(module: list[Modul]) -> QFrame:
    board = QFrame()
    board.setObjectName("board")
    layout = QVBoxLayout(board)
    layout.setContentsMargins(10, 10, 10, 8)
    layout.setSpacing(6)

    scroll = QScrollArea()
    scroll.setObjectName("boardScroll")
    scroll.viewport().setObjectName("boardViewport")
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    inhalt = QWidget()
    inhalt.setObjectName("boardInhalt")
    spalten = QHBoxLayout(inhalt)
    spalten.setContentsMargins(10, 10, 10, 10)
    spalten.setSpacing(20)
    for titel, status, bearbeitungsstatus in (
        ("Noch zu tun", "offen", Bearbeitungsstatus.NOCH_ZU_TUN),
        ("In Bearbeitung", "aktiv", Bearbeitungsstatus.IN_BEARBEITUNG),
        ("Fertig", "fertig", Bearbeitungsstatus.FERTIG),
    ):
        passende_module = [m for m in module if m.status == bearbeitungsstatus]
        spalten.addWidget(kanbanspalte(titel, status, passende_module), 1)
    scroll.setWidget(inhalt)
    layout.addWidget(scroll, 1)

    return board


class DashboardFenster(QMainWindow):
    def __init__(self, studiengang: Studiengang) -> None:
        super().__init__()
        self.studiengang = studiengang
        self.setWindowTitle("Studien-Dashboard")
        self.resize(1160, 827)
        self.setMinimumSize(960, 600)

        zentral = QWidget()
        zentral.setObjectName("dashboard")
        self.setCentralWidget(zentral)
        layout = QVBoxLayout(zentral)
        layout.setContentsMargins(26, 12, 26, 24)
        layout.setSpacing(18)

        kopf = QVBoxLayout()
        kopf.setSpacing(2)
        titel = label(studiengang.bezeichnung, "studiengang")
        titel.setWordWrap(True)
        titel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        titel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kopf.addWidget(titel)
        kurzinfo = f"{studiengang.regelstudienzeit} Semester · {studiengang.gesamt_ects} ECTS"
        if studiengang.zielnote is not None:
            kurzinfo += f" · Zielnote {dezimal(studiengang.zielnote)}"
        untertitel = label(kurzinfo, "muted")
        untertitel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kopf.addWidget(untertitel)
        layout.addLayout(kopf)

        kennzahlen = QHBoxLayout()
        kennzahlen.setSpacing(20)
        kennzahlen.addWidget(studienfortschritt(studiengang), 1)
        kennzahlen.addWidget(zeitplan(studiengang), 1)
        layout.addLayout(kennzahlen)

        board = QVBoxLayout()
        board.setSpacing(12)
        ueberschrift = QHBoxLayout()
        ueberschrift.addWidget(label("Module im Überblick", "boardTitel"))
        ueberschrift.addStretch()
        ueberschrift.addWidget(label(f"{len(studiengang.module)} Module", "muted"))
        board.addLayout(ueberschrift)
        board.addWidget(kanbanboard(studiengang.module), 1)
        layout.addLayout(board, 1)
