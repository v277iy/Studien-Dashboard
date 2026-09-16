from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QLineEdit,
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
    Studiengang,
)
from speicherung import speichern


class ModulDialog(QDialog):
    def __init__(
        self, studiengang: Studiengang, pfad: Path, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.studiengang = studiengang
        self.pfad = pfad
        self.modul: Modul | None = None
        self.setObjectName("modulDialog")
        self.setWindowTitle("Modul anlegen")
        self.resize(540, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        titel = QLabel("Modul anlegen")
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
        layout.addLayout(self.formular)

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
        self.name.textChanged.connect(self.eingabe_pruefen)
        self.code.textChanged.connect(self.eingabe_pruefen)
        self.semester.currentIndexChanged.connect(self.eingabe_pruefen)
        self.pruefungsform.currentIndexChanged.connect(self.eingabe_pruefen)
        self.eingabe_pruefen()
        self.name.setFocus()

    def feld_hinzufuegen(self, text: str, feld: QWidget) -> QLabel:
        beschriftung = QLabel(text)
        beschriftung.setBuddy(feld)
        zeile = self.formular.count() // 2
        self.formular.addWidget(beschriftung, zeile, 0)
        self.formular.addWidget(feld, zeile, 1)
        return beschriftung

    def eingabe_pruefen(self) -> None:
        klasse = self.pruefungsform.currentData()
        mehrteilig = klasse is not None and issubclass(klasse, MehrteiligePruefungsleistung)
        self.abschnitte.setVisible(mehrteilig)
        self.abschnitt_label.setVisible(mehrteilig)
        self.ok.setEnabled(bool(
            self.name.text().strip() and self.code.text().strip()
            and klasse is not None and self.semester.currentData() is not None
        ))

    def accept(self) -> None:
        self.eingabe_pruefen()
        if not self.ok.isEnabled():
            return
        klasse = self.pruefungsform.currentData()
        if issubclass(klasse, MehrteiligePruefungsleistung):
            pruefung = klasse(anzahl_abschnitte=self.abschnitte.value())
        else:
            pruefung = klasse()
        modul = Modul(
            modulcode=self.code.text().strip(),
            bezeichnung=self.name.text().strip(),
            ects=self.ects.value(),
            status=Bearbeitungsstatus.NOCH_ZU_TUN,
            pruefungsleistung=pruefung,
        )
        neuer_studiengang = deepcopy(self.studiengang)
        try:
            neuer_studiengang.modul_hinzufuegen(modul, self.semester.currentData())
            speichern(self.pfad, neuer_studiengang)
        except (OSError, ValueError) as fehler:
            self.fehler.setText(f"Speichern fehlgeschlagen: {fehler}")
            self.fehler.show()
            return
        self.modul = modul
        self.studiengang = neuer_studiengang
        super().accept()
