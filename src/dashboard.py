from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
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

from modul_dialog import ModulDialog
from modulliste import Modulleiste
from modelle import (
    Bearbeitungsstatus,
    MehrteiligePruefungsleistung,
    Modul,
    Prozent,
    Pruefungsergebnis,
    Studiengang,
)


def dezimal(wert: Decimal | None) -> str:
    return "—" if wert is None else f"{wert:.1f}".replace(".", ",")


def label(text: str, rolle: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setProperty("rolle", rolle)
    return widget


def balken(wert: Prozent = Decimal(0)) -> QProgressBar:
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
    kasten.setFixedHeight(150)

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
    links.addWidget(label(f"{erreicht} / {studiengang.gesamt_ects}", "wert"))
    fortschritt = QHBoxLayout()
    fortschritt.addWidget(balken(prozent), 1)
    fortschritt.addWidget(label(f"{prozent:.0f} %", "klein"))
    links.addLayout(fortschritt)

    rechts = QVBoxLayout()
    rechts.setSpacing(4)
    rechts.addWidget(label("Aktuelle Durchschnittsnote", "muted"))
    noten = QHBoxLayout()
    durchschnitt = studiengang.notendurchschnitt()
    wert = label(dezimal(durchschnitt), "wert")
    if durchschnitt is not None:
        wert.setToolTip("Ungerundet: " + format(durchschnitt, "f").replace(".", ","))
    noten.addWidget(wert)
    erreichtes_ziel = studiengang.zielnote_erreicht()
    zustand = "offen"
    if erreichtes_ziel is True:
        zieltext = "Zielnote erreicht"
        zustand = "erreicht"
    elif erreichtes_ziel is False:
        zieltext = "Zielnote noch nicht erreicht"
        zustand = "verfehlt"
    elif studiengang.zielnote is None:
        zieltext = "Keine Zielnote festgelegt"
    else:
        zieltext = "Noch keine Noten"
    if studiengang.zielnote is not None:
        ziel = label(f"Ziel: {dezimal(studiengang.zielnote)}", "ziel")
        ziel.setProperty("zustand", zustand)
        ziel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ziel.setFixedHeight(23)
        noten.addWidget(ziel)
    noten.addStretch()
    rechts.addLayout(noten)
    offen = max(0, studiengang.gesamt_ects - erreicht)
    rechts.addWidget(label(f"{offen} ECTS noch offen", "klein"))
    vergleich = label(zieltext, "zielstatus")
    vergleich.setProperty("zustand", zustand)
    rechts.addWidget(vergleich)
    return kennzahlenkasten("Studienfortschritt", links, rechts)


def zeitplan(studiengang: Studiengang) -> QFrame:
    heute = date.today()
    aktuell = studiengang.aktuelles_semester()
    semestertext = (
        f"Aktuelles Semester: {aktuell}" if aktuell is not None else "Keine offenen Module"
    )
    start = studiengang.startdatum.strftime("%d.%m.%Y")
    verbleibend = studiengang.verbleibende_semester()
    tage = studiengang.verbleibende_tage(heute)
    einheit = "Tag" if abs(tage) == 1 else "Tage"
    restzeit = f"Noch {tage} {einheit}" if tage > 0 else f"Um {-tage} {einheit} überzogen"
    if tage == 0:
        restzeit = "Enddatum heute"
    spalten = []
    for titel, datum, zusatz, detail in (
        ("Aktuelles Datum", heute, semestertext, f"Studienstart: {start}"),
        ("Geplantes Enddatum", studiengang.enddatum, f"Noch {verbleibend} Semester", restzeit),
    ):
        spalte = QVBoxLayout()
        spalte.setSpacing(4)
        spalte.addWidget(label(titel, "muted"))
        spalte.addWidget(label(datum.strftime("%d.%m.%Y"), "wert"))
        spalte.addWidget(label(zusatz, "klein"))
        spalte.addWidget(label(detail, "klein"))
        spalten.append(spalte)
    return kennzahlenkasten("Zeitplan", spalten[0], spalten[1])


class ModulKarte(QFrame):
    ausgewaehlt = Signal(str)

    def __init__(self, modulcode: str) -> None:
        super().__init__()
        self.modulcode = modulcode
        self.gedrueckt = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.gedrueckt = True
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            oeffnen = self.gedrueckt and self.rect().contains(event.position().toPoint())
            self.gedrueckt = False
            event.accept()
            if oeffnen:
                self.ausgewaehlt.emit(self.modulcode)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            event.accept()
            if not event.isAutoRepeat():
                self.ausgewaehlt.emit(self.modulcode)
        else:
            super().keyPressEvent(event)


def modulkarte(modul: Modul, status: str) -> QFrame:
    karte = ModulKarte(modul.modulcode)
    karte.setAccessibleName(f"Modul bearbeiten: {modul.bezeichnung}")
    karte.setObjectName("modulkarte")
    karte.setProperty("status", status)
    karte.setToolTip(modul.modulcode)
    pruefung = modul.pruefungsleistung
    fortschritt_anzeigen = (
        isinstance(pruefung, MehrteiligePruefungsleistung)
        and modul.status == Bearbeitungsstatus.IN_BEARBEITUNG
    )
    karte.setMinimumHeight(150 if fortschritt_anzeigen else 110)
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
    layout.addWidget(label(f"{pruefung.pruefungsform.value} · {modul.ects} ECTS", "muted"))

    if fortschritt_anzeigen:
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
    for widget in karte.findChildren(QWidget):
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
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


def dashboard_inhalt(studiengang: Studiengang) -> QWidget:
    inhalt = QWidget()
    inhalt.setObjectName("dashboard")
    layout = QVBoxLayout(inhalt)
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
    return inhalt


class DashboardFenster(QMainWindow):
    def __init__(self, studiengang: Studiengang, pfad: Path) -> None:
        super().__init__()
        self.studiengang = studiengang
        self.pfad = pfad
        self.setWindowTitle("Studien-Dashboard")
        self.resize(1400, 827)
        self.setMinimumSize(960, 600)

        zentral = QWidget()
        zentral.setObjectName("hauptfenster")
        self.setCentralWidget(zentral)
        self.hauptlayout = QHBoxLayout(zentral)
        self.hauptlayout.setContentsMargins(0, 0, 0, 0)
        self.hauptlayout.setSpacing(0)
        self.modulleiste = Modulleiste()
        self.modulleiste.neues_modul.connect(self.modul_anlegen)
        self.modulleiste.modul_gewaehlt.connect(self.modul_bearbeiten)
        self.hauptlayout.addWidget(self.modulleiste)
        self.inhalt: QWidget | None = None
        self.aktualisieren()

    def aktualisieren(self) -> None:
        self.modulleiste.anzeigen(self.studiengang.module)
        neuer_inhalt = dashboard_inhalt(self.studiengang)
        for karte in neuer_inhalt.findChildren(ModulKarte):
            karte.ausgewaehlt.connect(self.modul_bearbeiten)
        if self.inhalt is None:
            self.hauptlayout.addWidget(neuer_inhalt, 1)
        else:
            self.hauptlayout.replaceWidget(self.inhalt, neuer_inhalt)
            self.inhalt.setParent(None)
            self.inhalt.deleteLater()
        self.inhalt = neuer_inhalt

    def modul_anlegen(self) -> None:
        self.modul_dialog_oeffnen()

    def modul_bearbeiten(self, modulcode: str) -> None:
        self.modul_dialog_oeffnen(modulcode)

    def modul_dialog_oeffnen(self, modulcode: str | None = None) -> None:
        dialog = ModulDialog(self.studiengang, self.pfad, self, modulcode=modulcode)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.studiengang = dialog.studiengang
            self.aktualisieren()
            self.modulleiste.auswaehlen(dialog.modul.modulcode)
        dialog.deleteLater()
