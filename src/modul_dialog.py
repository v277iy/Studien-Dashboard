from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, QSignalBlocker, Qt
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
    EinteiligePruefungsleistung,
    MehrteiligePruefungsleistung,
    Modul,
    Pruefungsform,
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
        if modulcode is None:
            fenstertitel = "Modul anlegen"
            self.resize(540, 440)
        else:
            fenstertitel = "Modul bearbeiten"
            self.resize(580, 650)
        self.setWindowTitle(fenstertitel)

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
        self.ects = QSpinBox()
        self.ects.setRange(1, 10000)
        self.ects.setValue(5)
        self.feld_hinzufuegen("ECTS-Punkte", self.ects)
        self.semester = QComboBox()
        for nummer in range(1, studiengang.regelstudienzeit + 1):
            self.semester.addItem(str(nummer), nummer)
        self.feld_hinzufuegen("Semester", self.semester)
        self.pruefungsform = QComboBox()
        for form in Pruefungsform:
            self.pruefungsform.addItem(form.value, form)
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
            self.status.currentIndexChanged.connect(self.status_gewaehlt)
            self.ergebnis.currentIndexChanged.connect(self.ergebnis_gewaehlt)
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
        self.status.setToolTip("Fertig und das Prüfungsergebnis Bestanden werden gemeinsam gesetzt.")
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
        self.pruefungsform.setCurrentIndex(self.pruefungsform.findData(pruefung.pruefungsform))
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
        self.ects.setMaximum(max(10000, modul.ects))
        self.ects.setValue(modul.ects)
        if pruefung.note is not None:
            self.note.setDecimals(max(1, -pruefung.note.as_tuple().exponent))
            self.note.setValue(float(pruefung.note))

    def note_bearbeitet(self) -> None:
        self.note_geaendert = True

    def status_gewaehlt(self) -> None:
        # FERTIG und BESTANDEN werden zusammen gesetzt.
        # QSignalBlocker verhindert, dass die Auswahlfelder sich gegenseitig auslösen.
        if self.status.currentData() == Bearbeitungsstatus.FERTIG:
            with QSignalBlocker(self.ergebnis):
                self.ergebnis.setCurrentIndex(self.ergebnis.findData(Pruefungsergebnis.BESTANDEN))
        elif self.ergebnis.currentData() == Pruefungsergebnis.BESTANDEN:
            # Ein bewusst wieder geöffnetes Modul wartet auf ein neues Ergebnis.
            with QSignalBlocker(self.ergebnis):
                self.ergebnis.setCurrentIndex(self.ergebnis.findData(Pruefungsergebnis.AUSSTEHEND))
        self.eingabe_pruefen()

    def ergebnis_gewaehlt(self) -> None:
        # NOCH_ZU_TUN bleibt bestehen. Die Feldaktualisierung setzt das Ergebnis zurück.
        if self.status.currentData() != Bearbeitungsstatus.NOCH_ZU_TUN:
            status = (
                Bearbeitungsstatus.FERTIG
                if self.ergebnis.currentData() == Pruefungsergebnis.BESTANDEN
                else Bearbeitungsstatus.IN_BEARBEITUNG
            )
            with QSignalBlocker(self.status):
                self.status.setCurrentIndex(self.status.findData(status))
        self.eingabe_pruefen()

    def eingabe_pruefen(self) -> None:
        form = self.pruefungsform.currentData()
        mehrteilig = form is not None and Pruefungsform(form).ist_mehrteilig()
        bearbeiten = self.alter_code is not None
        self.abschnitte.setVisible(mehrteilig or bearbeiten)
        self.abschnitt_label.setVisible(mehrteilig or bearbeiten)
        self.abschnitte.setEnabled(mehrteilig)
        self.abschnitt_label.setEnabled(mehrteilig)
        gueltig = form is not None and self.semester.currentData() is not None
        if bearbeiten:
            self.bearbeitungsfelder_aktualisieren(mehrteilig)
            status = self.status.currentData()
            if status is None:
                gueltig = False
            ergebnis = self.ergebnis.currentData()
            if status != Bearbeitungsstatus.NOCH_ZU_TUN and ergebnis is None:
                gueltig = False
            if status == Bearbeitungsstatus.FERTIG and ergebnis != Pruefungsergebnis.BESTANDEN:
                gueltig = False
        if not self.name.text().strip() or not self.code.text().strip():
            gueltig = False
        self.ok.setEnabled(gueltig)

    def bearbeitungsfelder_aktualisieren(self, mehrteilig: bool) -> None:
        # Status und Ergebnis bestimmen, welche Angaben möglich sind.
        # Beim Wechsel werden unpassende Angaben zurückgesetzt.
        # Die 0 zeigt leere Zahlenfelder an. Im Modell stehen fehlende Angaben als None.
        status = self.status.currentData()
        begonnen = status in (Bearbeitungsstatus.IN_BEARBEITUNG, Bearbeitungsstatus.FERTIG)
        aktuell = mehrteilig and status == Bearbeitungsstatus.IN_BEARBEITUNG
        self.aktueller_abschnitt.setEnabled(aktuell)
        self.aktuell_label.setEnabled(aktuell)
        self.aktueller_abschnitt.setSpecialValueText("" if aktuell else "—")
        self.aktueller_abschnitt.setRange(1 if aktuell else 0, self.abschnitte.value())
        if not aktuell:
            self.aktueller_abschnitt.setValue(0)
        self.termin.setEnabled(self.termin_festgelegt.isChecked())
        self.ergebnis.setEnabled(begonnen)
        self.ergebnis_label.setEnabled(begonnen)
        if not begonnen:
            with QSignalBlocker(self.ergebnis):
                self.ergebnis.setCurrentIndex(self.ergebnis.findData(Pruefungsergebnis.AUSSTEHEND))

        ergebnis = self.ergebnis.currentData()
        note_erlaubt = begonnen and ergebnis in (
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
            # Eine neu aktivierte Note bekommt einen zum Ergebnis passenden Vorschlag.
            if ergebnis == Pruefungsergebnis.NICHT_BESTANDEN:
                self.note.setValue(5)
            else:
                self.note.setValue(2)

    def modul_aus_eingaben(self) -> Modul:
        form = Pruefungsform(self.pruefungsform.currentData())
        if form.ist_mehrteilig():
            pruefung = MehrteiligePruefungsleistung(
                pruefungsform=form, anzahl_abschnitte=self.abschnitte.value()
            )
        else:
            pruefung = EinteiligePruefungsleistung(pruefungsform=form)

        status = Bearbeitungsstatus.NOCH_ZU_TUN
        if self.alter_code is not None:
            status = Bearbeitungsstatus(self.status.currentData())
            if self.termin_festgelegt.isChecked():
                pruefung.termin = self.termin.date().toPython()
            if form.ist_mehrteilig() and status == Bearbeitungsstatus.IN_BEARBEITUNG:
                pruefung.aktueller_abschnitt = self.aktueller_abschnitt.value()
            if status != Bearbeitungsstatus.NOCH_ZU_TUN:
                pruefung.ergebnis = Pruefungsergebnis(self.ergebnis.currentData())
                if self.benotet.isChecked():
                    self.note.interpretText()
                    if self.note_geaendert:
                        pruefung.note = Decimal(self.note.cleanText().replace(",", "."))
                    else:
                        # Ohne Bearbeitung bleibt der genaue Decimal-Wert erhalten.
                        # Die Umwandlung über das Anzeigefeld kann Nachkommastellen verlieren.
                        pruefung.note = self.note_original

        return Modul(
            modulcode=self.code.text().strip(),
            bezeichnung=self.name.text().strip(),
            ects=self.ects.value(),
            status=status,
            pruefungsleistung=pruefung,
        )

    def accept(self) -> None:
        self.eingabe_pruefen()
        if not self.ok.isEnabled():
            return
        try:
            modul = self.modul_aus_eingaben()
            # Das Original bleibt bei Abbruch oder Schreibfehlern unverändert.
            neuer_studiengang = deepcopy(self.studiengang)
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
        # Die neue Version wird erst nach erfolgreichem Speichern übernommen.
        self.modul = modul
        self.studiengang = neuer_studiengang
        super().accept()
