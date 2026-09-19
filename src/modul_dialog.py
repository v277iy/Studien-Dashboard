from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from modelle import (
    Bearbeitungsstatus,
    Fallstudie,
    Klausur,
    MehrteiligePruefungsleistung,
    Modul,
    Portfolio,
    Projektpraesentation,
    Pruefungsergebnis,
    Studiengang,
)
from speicherung import speichern


class ModulDialog(QDialog):
    def __init__(
        self, studiengang: Studiengang, pfad: Path, parent: QWidget | None = None,
        *, modulcode: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.studiengang = studiengang
        self.pfad = pfad
        self.modul: Modul | None = None
        self.alter_code = modulcode
        self.setObjectName("modulDialog")
        fenstertitel = "Modul bearbeiten" if modulcode is not None else "Modul anlegen"
        self.setWindowTitle(fenstertitel)
        self.resize(580, 650) if modulcode is not None else self.resize(540, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        titel = QLabel(fenstertitel)
        titel.setProperty("rolle", "boardTitel")
        layout.addWidget(titel)

        self.formular = QGridLayout()
        self.formular.setSpacing(12)
        self.formular.setColumnStretch(1, 1)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Name des Moduls")
        self.feld_hinzufuegen("Name", self.name)
        self.code = QLineEdit()
        self.code.setPlaceholderText("Modulcode")
        self.feld_hinzufuegen("Modulcode", self.code)
        self.ects = QDoubleSpinBox()
        self.ects.setDecimals(1)
        self.ects.setRange(0.5, 10000)
        self.ects.setSingleStep(0.5)
        self.ects.setValue(5)
        self.feld_hinzufuegen("ECTS-Punkte", self.ects)
        self.semester = QComboBox()
        for nummer in range(1, studiengang.regelstudienzeit + 1):
            self.semester.addItem(str(nummer), nummer)
        self.feld_hinzufuegen("Semester", self.semester)
        self.pruefungsform = QComboBox()
        for klasse in (Klausur, Fallstudie, Portfolio, Projektpraesentation):
            name = klasse.__name__.replace("Projektpraesentation", "Projektpräsentation")
            self.pruefungsform.addItem(name, klasse)
        self.feld_hinzufuegen("Prüfungsform", self.pruefungsform)
        self.abschnitte = QSpinBox()
        self.abschnitte.setRange(1, 100)
        self.abschnitt_label = self.feld_hinzufuegen("Anzahl Abschnitte", self.abschnitte)
        for widget in (self.abschnitte, self.abschnitt_label):
            groesse = widget.sizePolicy()
            groesse.setRetainSizeWhenHidden(True)
            widget.setSizePolicy(groesse)
        if self.alter_code is None:
            layout.addLayout(self.formular)
        else:
            self.bearbeitungsfelder()
            self.formular.setContentsMargins(0, 0, 0, 0)
            inhalt = QWidget()
            inhalt.setObjectName("modulFormular")
            inhalt.setLayout(self.formular)
            scroll = QScrollArea()
            scroll.setObjectName("modulFormScroll")
            scroll.viewport().setObjectName("modulFormViewport")
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setWidget(inhalt)
            layout.addWidget(scroll, 1)

        self.fehler = QLabel()
        self.fehler.setProperty("rolle", "fehler")
        self.fehler.setTextFormat(Qt.TextFormat.PlainText)
        self.fehler.setWordWrap(True)
        self.fehler.hide()
        layout.addWidget(self.fehler)
        layout.addStretch()

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok = knoepfe.button(QDialogButtonBox.StandardButton.Ok)
        self.ok.setText("Ok")
        knoepfe.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        layout.addWidget(knoepfe)
        if self.alter_code is not None:
            self.werte_laden()
            self.status.currentIndexChanged.connect(self.eingabe_pruefen)
            self.ergebnis.currentIndexChanged.connect(self.eingabe_pruefen)
            self.termin_festgelegt.toggled.connect(self.eingabe_pruefen)
            self.benotet.toggled.connect(self.eingabe_pruefen)
        self.name.textChanged.connect(self.eingabe_pruefen)
        self.code.textChanged.connect(self.eingabe_pruefen)
        self.semester.currentIndexChanged.connect(self.eingabe_pruefen)
        self.pruefungsform.currentIndexChanged.connect(self.eingabe_pruefen)
        self.abschnitte.valueChanged.connect(self.eingabe_pruefen)
        self.eingabe_pruefen()
        if self.alter_code is not None:
            self.note_geaendert = False
            self.note.valueChanged.connect(self.note_bearbeitet)
            self.note.lineEdit().textEdited.connect(self.note_bearbeitet)
        self.name.setFocus()

    def feld_hinzufuegen(self, text: str, feld: QWidget) -> QLabel:
        beschriftung = QLabel(text)
        beschriftung.setBuddy(feld)
        zeile = self.formular.count() // 2
        self.formular.addWidget(beschriftung, zeile, 0)
        self.formular.addWidget(feld, zeile, 1)
        return beschriftung

    def bearbeitungsfelder(self) -> None:
        self.status = QComboBox()
        for text, status in (
            ("Noch zu tun", Bearbeitungsstatus.NOCH_ZU_TUN),
            ("In Bearbeitung", Bearbeitungsstatus.IN_BEARBEITUNG),
            ("Fertig", Bearbeitungsstatus.FERTIG),
        ):
            self.status.addItem(text, status)
        self.feld_hinzufuegen("Bearbeitungsstatus", self.status)
        self.aktueller_abschnitt = QSpinBox()
        self.aktueller_abschnitt.setRange(0, self.abschnitte.value())
        self.aktuell_label = self.feld_hinzufuegen("Aktueller Abschnitt", self.aktueller_abschnitt)

        terminfeld = QWidget()
        terminlayout = QHBoxLayout(terminfeld)
        terminlayout.setContentsMargins(0, 0, 0, 0)
        self.termin_festgelegt = QCheckBox("Festgelegt")
        self.termin = QDateEdit(QDate.currentDate())
        self.termin.setDateRange(QDate(1, 1, 1), QDate(9999, 12, 31))
        self.termin.setDisplayFormat("dd.MM.yyyy")
        self.termin.setCalendarPopup(True)
        terminlayout.addWidget(self.termin_festgelegt)
        terminlayout.addWidget(self.termin, 1)
        self.feld_hinzufuegen("Prüfungstermin", terminfeld)

        self.ergebnis = QComboBox()
        for text, ergebnis in (
            ("Ausstehend", Pruefungsergebnis.AUSSTEHEND),
            ("Bestanden", Pruefungsergebnis.BESTANDEN),
            ("Nicht bestanden", Pruefungsergebnis.NICHT_BESTANDEN),
        ):
            self.ergebnis.addItem(text, ergebnis)
        self.ergebnis_label = self.feld_hinzufuegen("Prüfungsergebnis", self.ergebnis)

        notenfeld = QWidget()
        notenlayout = QHBoxLayout(notenfeld)
        notenlayout.setContentsMargins(0, 0, 0, 0)
        self.benotet = QCheckBox("Benotet")
        self.note = QDoubleSpinBox()
        self.note.setLocale(QLocale("de_DE"))
        self.note.setDecimals(1)
        self.note.setRange(0, 5)
        self.note.setSingleStep(0.1)
        notenlayout.addWidget(self.benotet)
        notenlayout.addWidget(self.note, 1)
        self.note_label = self.feld_hinzufuegen("Note", notenfeld)

    def werte_laden(self) -> None:
        semester, modul = self.studiengang.modul_finden(self.alter_code)
        pruefung = modul.pruefungsleistung
        self.note_original = pruefung.note
        self.name.setText(modul.bezeichnung)
        self.code.setText(modul.modulcode)
        if self.semester.findData(semester.nummer) < 0:
            self.semester.addItem(str(semester.nummer), semester.nummer)
        self.semester.setCurrentIndex(self.semester.findData(semester.nummer))
        self.pruefungsform.setCurrentIndex(self.pruefungsform.findData(type(pruefung)))
        self.status.setCurrentIndex(self.status.findData(modul.status))
        self.ergebnis.setCurrentIndex(self.ergebnis.findData(pruefung.ergebnis))
        if isinstance(pruefung, MehrteiligePruefungsleistung):
            self.abschnitte.setMaximum(max(100, pruefung.anzahl_abschnitte))
            self.abschnitte.setValue(pruefung.anzahl_abschnitte)
            self.aktueller_abschnitt.setMaximum(pruefung.anzahl_abschnitte)
            self.aktueller_abschnitt.setValue(pruefung.aktueller_abschnitt or 0)
        self.termin_festgelegt.setChecked(pruefung.termin is not None)
        if pruefung.termin is not None:
            self.termin.setDate(QDate(
                pruefung.termin.year, pruefung.termin.month, pruefung.termin.day
            ))
        self.benotet.setChecked(pruefung.note is not None)
        for feld, wert in ((self.ects, modul.ects), (self.note, pruefung.note)):
            if wert is not None:
                feld.setDecimals(max(1, -Decimal(str(wert)).as_tuple().exponent))
                anzeigewert = float(wert)
                feld.setRange(min(feld.minimum(), anzeigewert), max(feld.maximum(), anzeigewert))
                feld.setValue(anzeigewert)

    def note_bearbeitet(self) -> None:
        self.note_geaendert = True

    def eingabe_pruefen(self) -> None:
        klasse = self.pruefungsform.currentData()
        mehrteilig = klasse is not None and issubclass(klasse, MehrteiligePruefungsleistung)
        bearbeiten = self.alter_code is not None
        self.abschnitte.setVisible(mehrteilig or bearbeiten)
        self.abschnitt_label.setVisible(mehrteilig or bearbeiten)
        self.abschnitte.setEnabled(mehrteilig)
        self.abschnitt_label.setEnabled(mehrteilig)
        gueltig = klasse is not None and self.semester.currentData() is not None
        if bearbeiten:
            status = self.status.currentData()
            fertig = status == Bearbeitungsstatus.FERTIG
            aktuell = mehrteilig and status == Bearbeitungsstatus.IN_BEARBEITUNG
            self.aktueller_abschnitt.setEnabled(aktuell)
            self.aktuell_label.setEnabled(aktuell)
            self.aktueller_abschnitt.setSpecialValueText("" if aktuell else "—")
            self.aktueller_abschnitt.setRange(1 if aktuell else 0, self.abschnitte.value())
            if not aktuell:
                self.aktueller_abschnitt.setValue(0)
            self.termin.setEnabled(self.termin_festgelegt.isChecked())
            self.ergebnis.setEnabled(fertig)
            self.ergebnis_label.setEnabled(fertig)
            if not fertig:
                self.ergebnis.setCurrentIndex(0)
            ergebnis = self.ergebnis.currentData()
            note_erlaubt = fertig and ergebnis in (
                Pruefungsergebnis.BESTANDEN, Pruefungsergebnis.NICHT_BESTANDEN
            )
            self.benotet.setEnabled(note_erlaubt)
            self.note_label.setEnabled(note_erlaubt)
            if not note_erlaubt:
                self.benotet.setChecked(False)
            benotet = note_erlaubt and self.benotet.isChecked()
            self.note.setEnabled(benotet)
            leer = self.note.value() == 0
            self.note.setSpecialValueText("" if benotet else "—")
            self.note.setRange(1 if benotet else 0, 5)
            if not benotet:
                self.note.setValue(0)
            elif leer:
                self.note.setValue(5 if ergebnis == Pruefungsergebnis.NICHT_BESTANDEN else 2)
            gueltig = gueltig and status is not None and (not fertig or ergebnis is not None)
        self.ok.setEnabled(bool(
            self.name.text().strip() and self.code.text().strip() and gueltig
        ))

    def accept(self) -> None:
        self.eingabe_pruefen()
        if not self.ok.isEnabled():
            return
        klasse = self.pruefungsform.currentData()
        status = Bearbeitungsstatus.NOCH_ZU_TUN
        werte = {}
        if self.alter_code is not None:
            status = Bearbeitungsstatus(self.status.currentData())
            werte["termin"] = (
                self.termin.date().toPython() if self.termin_festgelegt.isChecked() else None
            )
            if status == Bearbeitungsstatus.FERTIG:
                werte["ergebnis"] = Pruefungsergebnis(self.ergebnis.currentData())
                werte["note"] = None
                if self.benotet.isChecked():
                    self.note.interpretText()
                    werte["note"] = (
                        Decimal(self.note.cleanText().replace(",", "."))
                        if self.note_geaendert else self.note_original
                    )
        if issubclass(klasse, MehrteiligePruefungsleistung):
            werte["anzahl_abschnitte"] = self.abschnitte.value()
            if status == Bearbeitungsstatus.IN_BEARBEITUNG:
                werte["aktueller_abschnitt"] = self.aktueller_abschnitt.value()
        pruefung = klasse(**werte)
        modul = Modul(
            modulcode=self.code.text().strip(),
            bezeichnung=self.name.text().strip(),
            ects=self.ects.value(),
            status=status,
            pruefungsleistung=pruefung,
        )
        neuer_studiengang = deepcopy(self.studiengang)
        try:
            if self.alter_code is None:
                neuer_studiengang.modul_hinzufuegen(modul, self.semester.currentData())
            else:
                neuer_studiengang.modul_aktualisieren(
                    self.alter_code, modul, self.semester.currentData()
                )
            speichern(self.pfad, neuer_studiengang)
        except (OSError, ValueError) as fehler:
            self.fehler.setText(f"Speichern fehlgeschlagen: {fehler}")
            self.fehler.show()
            return
        self.modul = modul
        self.studiengang = neuer_studiengang
        super().accept()
