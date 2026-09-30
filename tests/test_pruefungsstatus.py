"""Regressionstests: Nur bestandene Module sind abgeschlossen."""
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication, QDialog
from modelle import (
    Bearbeitungsstatus as Status, EinteiligePruefungsleistung,
    MehrteiligePruefungsleistung, Modul, Pruefungsergebnis as Ergebnis,
    Pruefungsform, Semester, Studiengang,
)
from modul_dialog import ModulDialog
from speicherung import laden, modul_aus_dict, speichern


class PruefungsstatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def modul(self, status, ergebnis, mehrteilig=False):
        if mehrteilig:
            pruefung = MehrteiligePruefungsleistung(
                pruefungsform=Pruefungsform.PORTFOLIO, anzahl_abschnitte=3,
                aktueller_abschnitt=2 if status == Status.IN_BEARBEITUNG else None,
                ergebnis=ergebnis,
            )
        else:
            pruefung = EinteiligePruefungsleistung(
                pruefungsform=Pruefungsform.KLAUSUR, ergebnis=ergebnis,
            )
        return Modul("A", "Modul A", 5, status, pruefung)

    def test_gueltige_kombinationen(self):
        for mehrteilig in (False, True):
            for status in Status:
                for ergebnis in Ergebnis:
                    with self.subTest(status=status, ergebnis=ergebnis, mehrteilig=mehrteilig):
                        modul = self.modul(status, ergebnis, mehrteilig)
                        gueltig = (status, ergebnis) in (
                            (Status.NOCH_ZU_TUN, Ergebnis.AUSSTEHEND),
                            (Status.IN_BEARBEITUNG, Ergebnis.AUSSTEHEND),
                            (Status.IN_BEARBEITUNG, Ergebnis.NICHT_BESTANDEN),
                            (Status.FERTIG, Ergebnis.BESTANDEN),
                        )
                        if gueltig:
                            modul.angaben_pruefen()
                        else:
                            with self.assertRaises(ValueError):
                                modul.angaben_pruefen()

    def test_nicht_bestanden_mit_note(self):
        modul = self.modul(Status.IN_BEARBEITUNG, Ergebnis.NICHT_BESTANDEN)
        modul.pruefungsleistung.note = Decimal("5")
        modul.angaben_pruefen()
        modul.pruefungsleistung.note = Decimal("2")
        with self.assertRaises(ValueError):
            modul.angaben_pruefen()

    def test_semester_nur_mit_bestandener_pruefung_fertig(self):
        for ergebnis in Ergebnis:
            modul = self.modul(Status.FERTIG, ergebnis)
            semester = Semester(1, [modul])
            self.assertEqual(semester.ist_fertig(), ergebnis == Ergebnis.BESTANDEN)
            self.assertEqual(modul.fortschritt(), 100 if ergebnis == Ergebnis.BESTANDEN else 0)

    def test_alte_dateien_werden_korrigiert(self):
        for ergebnis in (Ergebnis.AUSSTEHEND, Ergebnis.NICHT_BESTANDEN):
            for mehrteilig in (False, True):
                with self.subTest(ergebnis=ergebnis, mehrteilig=mehrteilig):
                    pruefung = {"pruefungsform": "Portfolio" if mehrteilig else "Klausur",
                                "ergebnis": ergebnis}
                    if mehrteilig:
                        pruefung["anzahl_abschnitte"] = 3
                    modul = modul_aus_dict({
                        "modulcode": "A", "bezeichnung": "A", "ects": 5,
                        "status": "FERTIG", "pruefungsleistung": pruefung,
                    })
                    self.assertEqual(modul.status, Status.IN_BEARBEITUNG)
                    self.assertEqual(modul.pruefungsleistung.ergebnis, ergebnis)
                    modul.angaben_pruefen()
                    if mehrteilig:
                        self.assertEqual(modul.pruefungsleistung.aktueller_abschnitt, 3)

    def waehlen(self, feld, wert):
        feld.setCurrentIndex(feld.findData(wert))

    def test_dialog_und_speichern(self):
        for mehrteilig in (False, True):
            with self.subTest(mehrteilig=mehrteilig), TemporaryDirectory() as ordner:
                pfad = Path(ordner) / "Studiengang.json"
                studiengang = Studiengang("Studium", 6, 180, date(2026, 1, 1))
                studiengang.modul_hinzufuegen(
                    self.modul(Status.IN_BEARBEITUNG, Ergebnis.AUSSTEHEND, mehrteilig), 1,
                )
                speichern(pfad, studiengang)
                for ergebnis in (Ergebnis.NICHT_BESTANDEN, Ergebnis.BESTANDEN,
                                 Ergebnis.AUSSTEHEND):
                    dialog = ModulDialog(laden(pfad), pfad, modulcode="A")
                    self.assertTrue(dialog.ergebnis.isEnabled())
                    self.waehlen(dialog.ergebnis, ergebnis)
                    erwartet = Status.FERTIG if ergebnis == Ergebnis.BESTANDEN else Status.IN_BEARBEITUNG
                    self.assertEqual(dialog.status.currentData(), erwartet)
                    if ergebnis == Ergebnis.NICHT_BESTANDEN:
                        dialog.benotet.setChecked(True)
                        self.assertTrue(dialog.note.isEnabled())
                        dialog.note.setValue(5)
                    elif ergebnis == Ergebnis.BESTANDEN:
                        dialog.benotet.setChecked(False)
                    else:
                        self.assertFalse(dialog.note.isEnabled())
                    dialog.accept()
                    self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted, dialog.fehler.text())
                    gespeichert = laden(pfad).module[0]
                    self.assertEqual(gespeichert.status, erwartet)
                    self.assertEqual(gespeichert.pruefungsleistung.ergebnis, ergebnis)
                    gespeichert.angaben_pruefen()
                    self.assertEqual(laden(pfad).erreichte_ects(), 5 if ergebnis == Ergebnis.BESTANDEN else 0)
                    if ergebnis == Ergebnis.NICHT_BESTANDEN:
                        self.assertEqual(gespeichert.pruefungsleistung.note, Decimal(5))
                    dialog.deleteLater()

    def test_fertig_setzt_bestanden_und_wird_gespeichert(self):
        for mehrteilig in (False, True):
            for status, ergebnis in (
                (Status.NOCH_ZU_TUN, Ergebnis.AUSSTEHEND),
                (Status.IN_BEARBEITUNG, Ergebnis.AUSSTEHEND),
                (Status.IN_BEARBEITUNG, Ergebnis.NICHT_BESTANDEN),
            ):
                with self.subTest(mehrteilig=mehrteilig, status=status, ergebnis=ergebnis), TemporaryDirectory() as ordner:
                    pfad = Path(ordner) / "Studiengang.json"
                    studiengang = Studiengang("Studium", 6, 180, date(2026, 1, 1))
                    studiengang.modul_hinzufuegen(self.modul(status, ergebnis, mehrteilig), 1)
                    dialog = ModulDialog(studiengang, pfad, modulcode="A")
                    fertig = dialog.status.findData(Status.FERTIG)
                    self.assertTrue(dialog.status.model().item(fertig).isEnabled())
                    self.waehlen(dialog.status, Status.FERTIG)
                    self.assertEqual(dialog.ergebnis.currentData(), Ergebnis.BESTANDEN)
                    self.assertEqual(dialog.status.currentData(), Status.FERTIG)
                    self.assertTrue(dialog.ergebnis.isEnabled())
                    self.assertFalse(dialog.aktueller_abschnitt.isEnabled())
                    dialog.accept()
                    self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted, dialog.fehler.text())
                    modul = laden(pfad).module[0]
                    self.assertEqual(modul.status, Status.FERTIG)
                    self.assertEqual(modul.pruefungsleistung.ergebnis, Ergebnis.BESTANDEN)
                    modul.angaben_pruefen()
                    dialog.deleteLater()

    def test_noch_zu_tun_und_wieder_oeffnen(self):
        with TemporaryDirectory() as ordner:
            studiengang = Studiengang("Studium", 6, 180, date(2026, 1, 1))
            studiengang.modul_hinzufuegen(self.modul(Status.FERTIG, Ergebnis.BESTANDEN), 1)
            dialog = ModulDialog(studiengang, Path(ordner) / "Studiengang.json", modulcode="A")
            self.waehlen(dialog.status, Status.IN_BEARBEITUNG)
            self.assertTrue(dialog.ergebnis.isEnabled())
            self.assertEqual(dialog.ergebnis.currentData(), Ergebnis.AUSSTEHEND)
            self.assertTrue(dialog.status.model().item(dialog.status.findData(Status.FERTIG)).isEnabled())
            self.waehlen(dialog.ergebnis, Ergebnis.NICHT_BESTANDEN)
            self.waehlen(dialog.status, Status.NOCH_ZU_TUN)
            self.assertFalse(dialog.ergebnis.isEnabled())
            self.assertEqual(dialog.ergebnis.currentData(), Ergebnis.AUSSTEHEND)
            dialog.modul_aus_eingaben().angaben_pruefen()
            dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
