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
    QVBoxLayout,
    QWidget,
)


def label(text: str, rolle: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setProperty("rolle", rolle)
    return widget


def balken() -> QProgressBar:
    widget = QProgressBar()
    widget.setRange(0, 100)
    widget.setValue(0)
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


def studienfortschritt() -> QFrame:
    links = QVBoxLayout()
    links.setSpacing(4)
    links.addWidget(label("Erreichte ECTS", "muted"))
    links.addWidget(label("— / —", "wert"))
    fortschritt = QHBoxLayout()
    fortschritt.addWidget(balken(), 1)
    fortschritt.addWidget(label("— %", "klein"))
    links.addLayout(fortschritt)

    rechts = QVBoxLayout()
    rechts.setSpacing(4)
    rechts.addWidget(label("Aktuelle Durchschnittsnote", "muted"))
    noten = QHBoxLayout()
    noten.addWidget(label("—", "wert"))
    ziel = label("Ziel: —", "ziel")
    ziel.setAlignment(Qt.AlignmentFlag.AlignCenter)
    ziel.setFixedHeight(23)
    noten.addWidget(ziel)
    noten.addStretch()
    rechts.addLayout(noten)
    rechts.addWidget(label("— ECTS noch offen", "klein"))
    return kennzahlenkasten("Studienfortschritt", links, rechts)


def zeitplan() -> QFrame:
    spalten = []
    for titel, zusatz in (
        ("Aktuelles Datum", "Aktuelles Semester: —"),
        ("Geplantes Enddatum", "Noch — Semester"),
    ):
        spalte = QVBoxLayout()
        spalte.setSpacing(4)
        spalte.addWidget(label(titel, "muted"))
        spalte.addWidget(label("TT.MM.JJJJ", "wert"))
        spalte.addWidget(label(zusatz, "klein"))
        spalten.append(spalte)
    return kennzahlenkasten("Zeitplan", spalten[0], spalten[1])


def modulkarte(status: str, variante: str) -> QFrame:
    karte = QFrame()
    karte.setObjectName("modulkarte")
    karte.setProperty("status", status)
    hoehe = 126 if status == "aktiv" else 121 if variante == "abschnitte" else 110
    karte.setFixedHeight(hoehe)

    schatten = QGraphicsDropShadowEffect(karte)
    schatten.setBlurRadius(12)
    schatten.setOffset(0, 3)
    schatten.setColor(QColor(23, 32, 51, 32))
    karte.setGraphicsEffect(schatten)

    layout = QVBoxLayout(karte)
    layout.setContentsMargins(14, 12, 18, 18)
    layout.setSpacing(6)
    kopf = QHBoxLayout()
    kopf.addWidget(label("Modulname", "titel"))
    kopf.addStretch()
    kopf.addWidget(label("⋯", "muted"))
    layout.addLayout(kopf)
    layout.addWidget(label("Prüfungsform · — ECTS", "muted"))

    if variante in ("abschnitte", "fortschritt"):
        layout.addWidget(label("Aktueller Abschnitt: — von —", "klein"))
        fortschritt = balken()
        fortschritt.setProperty("status", status)
        layout.addWidget(fortschritt)
        if variante == "fortschritt":
            prozent = label("— %", "prozent")
            prozent.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(prozent)
    else:
        layout.addSpacing(4)
        unten = QHBoxLayout()
        badge = label("STATUS: —", "status")
        badge.setProperty("status", status)
        badge.setFixedHeight(23)
        unten.addWidget(badge)
        unten.addStretch()
        if variante == "termin":
            titel = "Prüfung" if status == "aktiv" else "Termin"
            unten.addWidget(label(f"{titel}: —.—.", "klein"))
        elif variante == "note":
            unten.addWidget(label("Note: —", "note"))
        layout.addLayout(unten)
    layout.addStretch()
    return karte


def kanbanspalte(titel: str, status: str, varianten: tuple[str, ...]) -> QWidget:
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
    anzahl = label("—", "anzahl")
    anzahl.setFixedSize(25, 23)
    anzahl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    kopf_layout.addWidget(anzahl)
    layout.addWidget(kopf)

    for variante in varianten:
        layout.addWidget(modulkarte(status, variante))
    layout.addStretch()
    return spalte


def kanbanboard() -> QFrame:
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
    for titel, status, varianten in (
        ("Noch zu tun", "offen", ("termin", "abschnitte", "status")),
        ("In Bearbeitung", "aktiv", ("fortschritt", "termin")),
        ("Fertig", "fertig", ("note", "note", "note")),
    ):
        spalten.addWidget(kanbanspalte(titel, status, varianten), 1)
    scroll.setWidget(inhalt)
    layout.addWidget(scroll, 1)

    return board


class DashboardFenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
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
        titel = label("Studiengang", "studiengang")
        titel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kopf.addWidget(titel)
        untertitel = label("— Semester · — ECTS · Zielnote —", "muted")
        untertitel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kopf.addWidget(untertitel)
        layout.addLayout(kopf)

        kennzahlen = QHBoxLayout()
        kennzahlen.setSpacing(20)
        kennzahlen.addWidget(studienfortschritt(), 1)
        kennzahlen.addWidget(zeitplan(), 1)
        layout.addLayout(kennzahlen)

        board = QVBoxLayout()
        board.setSpacing(12)
        ueberschrift = QHBoxLayout()
        ueberschrift.addWidget(label("Module im Überblick", "boardTitel"))
        ueberschrift.addStretch()
        ueberschrift.addWidget(label("Platzhalter – noch ohne Funktion", "muted"))
        board.addLayout(ueberschrift)
        board.addWidget(kanbanboard(), 1)
        layout.addLayout(board, 1)
