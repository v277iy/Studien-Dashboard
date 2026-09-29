from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from modelle import Semester, Studiengang
from speicherung import speichern


class StudiengangDialog(QDialog):
    def __init__(self, pfad: Path, hinweis: str = "") -> None:
        super().__init__()
        self.pfad = pfad
        self.studiengang: Studiengang | None = None
        self.setObjectName("einrichtung")
        self.setWindowTitle("Studiengang anlegen")
        self.resize(540, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        titel = QLabel("Studiengang anlegen")
        titel.setProperty("rolle", "boardTitel")
        layout.addWidget(titel)
        if hinweis:
            meldung = QLabel(hinweis)
            meldung.setTextFormat(Qt.TextFormat.PlainText)
            meldung.setWordWrap(True)
            layout.addWidget(meldung)

        formular = QFormLayout()
        formular.setSpacing(12)
        formular.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Name des Studiengangs")
        formular.addRow("Name", self.name)
        self.semester = QSpinBox()
        self.semester.setRange(1, 100)
        self.semester.setValue(6)
        formular.addRow("Anzahl Semester", self.semester)
        self.ects = QSpinBox()
        self.ects.setRange(1, 10000)
        self.ects.setValue(180)
        formular.addRow("ECTS-Punkte", self.ects)
        self.zielnote = QDoubleSpinBox()
        self.zielnote.setLocale(QLocale("de_DE"))
        self.zielnote.setDecimals(1)
        self.zielnote.setRange(1.0, 5.0)
        self.zielnote.setSingleStep(0.1)
        self.zielnote.setValue(2.0)
        formular.addRow("Zielnote", self.zielnote)
        self.startdatum = QDateEdit(QDate.currentDate())
        self.startdatum.setDisplayFormat("dd.MM.yyyy")
        self.startdatum.setCalendarPopup(True)
        self.startdatum.setDateRange(QDate(1, 1, 1), QDate(9999, 12, 31))
        formular.addRow("Startdatum", self.startdatum)
        layout.addLayout(formular)

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
        self.ok.setEnabled(False)
        knoepfe.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.name.textChanged.connect(self.eingabe_pruefen)
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        layout.addWidget(knoepfe)
        self.name.setFocus()

    def eingabe_pruefen(self) -> None:
        name = self.name.text().strip()
        self.ok.setEnabled(name != "")

    def accept(self) -> None:
        if not self.name.text().strip():
            self.name.setFocus()
            return
        self.zielnote.interpretText()
        try:
            studiengang = Studiengang(
                bezeichnung=self.name.text().strip(),
                regelstudienzeit=self.semester.value(),
                gesamt_ects=self.ects.value(),
                zielnote=Decimal(self.zielnote.cleanText().replace(",", ".")),
                startdatum=self.startdatum.date().toPython(),
                semester=[Semester(nummer) for nummer in range(1, self.semester.value() + 1)],
            )
            speichern(self.pfad, studiengang, sichern=True)
        except (OSError, ValueError) as fehler:
            self.fehler.setText(f"Speichern fehlgeschlagen: {fehler}")
            self.fehler.show()
            return
        self.studiengang = studiengang
        super().accept()
