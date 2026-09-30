from copy import deepcopy
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from PySide6.QtCore import QDate, QEvent, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QProgressBar

from dashboard import DashboardFenster, ModulKarte
from modelle import (
    Bearbeitungsstatus, EinteiligePruefungsleistung, MehrteiligePruefungsleistung,
    Pruefungsergebnis, Pruefungsform,
)
from modul_dialog import ModulDialog
from speicherung import laden, speichern


BEISPIEL = Path(__file__).with_name("daten") / "Studiengang.json"


class BearbeitungTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setApplicationName("Studien-Dashboard")
        cls.app.setQuitOnLastWindowClosed(False)
        cls.app.setStyleSheet((SRC / "style.qss").read_text(encoding="utf-8"))

    def setUp(self):
        self.ordner = TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.pfad = Path(self.ordner.name) / "Studiengang.json"
        self.studiengang = laden(BEISPIEL)
        speichern(self.pfad, self.studiengang)

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def dialog(self, code):
        dialog = ModulDialog(self.studiengang, self.pfad, modulcode=code)
        dialog.show()
        self.app.processEvents()
        return dialog

    def fenster(self):
        fenster = DashboardFenster(self.studiengang, self.pfad)
        fenster.show()
        fenster.activateWindow()
        self.app.processEvents()
        return fenster

    def waehlen(self, feld, wert):
        index = feld.findData(wert)
        self.assertGreaterEqual(index, 0)
        feld.setCurrentIndex(index)

    def ausloesen(self, ausloeser, aktion):
        fehler = []
        geoeffnet = []

        def eingeben():
            dialog = self.app.activeModalWidget()
            try:
                self.assertIsInstance(dialog, ModulDialog)
                geoeffnet.append(dialog.alter_code)
                aktion(dialog)
            except BaseException as problem:
                fehler.append(problem)
            finally:
                if dialog is not None and dialog.isVisible():
                    dialog.reject()

        QTimer.singleShot(0, eingeben)
        ausloeser()
        self.app.processEvents()
        if fehler:
            raise fehler[0]
        self.assertEqual(len(geoeffnet), 1)

    def test_vorhandene_werte_werden_vorbelegt(self):
        vorher = self.pfad.read_bytes()
        for semester in self.studiengang.semester:
            for modul in semester.module:
                dialog = self.dialog(modul.modulcode)
                pruefung = modul.pruefungsleistung
                self.assertEqual(dialog.windowTitle(), "Modul bearbeiten")
                self.assertEqual(dialog.name.text(), modul.bezeichnung)
                self.assertEqual(dialog.code.text(), modul.modulcode)
                self.assertEqual(dialog.ects.value(), modul.ects)
                self.assertIs(type(dialog.ects.value()), int)
                self.assertEqual(dialog.semester.currentData(), semester.nummer)
                self.assertEqual(dialog.pruefungsform.currentData(), pruefung.pruefungsform)
                self.assertEqual(dialog.status.currentData(), modul.status)
                self.assertEqual(dialog.ergebnis.currentData(), pruefung.ergebnis)
                self.assertEqual(dialog.termin_festgelegt.isChecked(), pruefung.termin is not None)
                if pruefung.termin:
                    self.assertEqual(dialog.termin.date().toPython(), pruefung.termin)
                self.assertEqual(dialog.benotet.isChecked(), pruefung.note is not None)
                if pruefung.note is not None:
                    self.assertEqual(dialog.note.value(), float(pruefung.note))
                if isinstance(pruefung, MehrteiligePruefungsleistung):
                    self.assertEqual(dialog.abschnitte.value(), pruefung.anzahl_abschnitte)
                dialog.reject()
        self.assertEqual(self.pfad.read_bytes(), vorher)

    def test_code_semester_pruefungsform_und_termin_aendern(self):
        vorher = deepcopy(self.studiengang)
        dialog = self.dialog("OOP-PY")
        dialog.name.setText("  Überarbeitetes Projekt  ")
        dialog.code.setText("  PROJ-NEU  ")
        dialog.ects.setValue(7)
        self.waehlen(dialog.semester, 3)
        dialog.pruefungsform.setCurrentText("Projektpräsentation")
        dialog.abschnitte.setValue(6)
        dialog.aktueller_abschnitt.setValue(4)
        dialog.termin_festgelegt.setChecked(True)
        dialog.termin.setDate(QDate(2030, 4, 21))
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        geladen = laden(self.pfad)
        semester, modul = geladen.modul_finden("PROJ-NEU")
        self.assertEqual(semester.nummer, 3)
        self.assertEqual(modul.bezeichnung, "Überarbeitetes Projekt")
        self.assertEqual(modul.ects, 7)
        self.assertIs(type(modul.ects), int)
        self.assertEqual(modul.status, Bearbeitungsstatus.IN_BEARBEITUNG)
        self.assertIs(modul.pruefungsleistung.pruefungsform, Pruefungsform.PROJEKTPRAESENTATION)
        self.assertIsInstance(modul.pruefungsleistung, MehrteiligePruefungsleistung)
        self.assertEqual(modul.pruefungsleistung.termin, date(2030, 4, 21))
        self.assertEqual(modul.pruefungsleistung.anzahl_abschnitte, 6)
        self.assertEqual(modul.pruefungsleistung.aktueller_abschnitt, 4)
        self.assertEqual(len(geladen.module), len(vorher.module))
        with self.assertRaises(ValueError):
            geladen.modul_finden("OOP-PY")
        for alt in vorher.module:
            if alt.modulcode != "OOP-PY":
                self.assertEqual(geladen.modul_finden(alt.modulcode)[1], alt)
        self.assertEqual(self.studiengang, vorher)

    def test_relevante_felder_und_statuswechsel(self):
        dialog = self.dialog("OOP-PY")
        self.assertTrue(dialog.aktueller_abschnitt.isEnabled())
        self.assertEqual(dialog.aktueller_abschnitt.value(), 2)
        self.assertTrue(dialog.ergebnis.isEnabled())
        self.assertFalse(dialog.benotet.isEnabled())
        self.assertFalse(dialog.note.isEnabled())
        dialog.abschnitte.setValue(1)
        self.assertEqual(dialog.aktueller_abschnitt.maximum(), 1)
        self.assertEqual(dialog.aktueller_abschnitt.value(), 1)
        self.waehlen(dialog.status, Bearbeitungsstatus.NOCH_ZU_TUN)
        self.assertFalse(dialog.aktueller_abschnitt.isEnabled())
        self.assertEqual(dialog.aktueller_abschnitt.value(), 0)
        self.waehlen(dialog.status, Bearbeitungsstatus.IN_BEARBEITUNG)
        self.assertTrue(dialog.aktueller_abschnitt.isEnabled())
        self.assertTrue(dialog.ergebnis.isEnabled())
        self.assertFalse(dialog.benotet.isEnabled())
        self.waehlen(dialog.ergebnis, Pruefungsergebnis.BESTANDEN)
        self.assertEqual(dialog.status.currentData(), Bearbeitungsstatus.FERTIG)
        self.assertFalse(dialog.aktueller_abschnitt.isEnabled())
        self.assertTrue(dialog.benotet.isEnabled())
        self.assertFalse(dialog.note.isEnabled())
        dialog.benotet.setChecked(True)
        self.assertTrue(dialog.note.isEnabled())
        dialog.note.setValue(1.7)
        self.waehlen(dialog.status, Bearbeitungsstatus.NOCH_ZU_TUN)
        self.assertFalse(dialog.ergebnis.isEnabled())
        self.assertFalse(dialog.note.isEnabled())
        dialog.aktueller_abschnitt.setValue(1)
        dialog.note.setValue(2.0)
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        modul = laden(self.pfad).modul_finden("OOP-PY")[1]
        self.assertIsNone(modul.pruefungsleistung.aktueller_abschnitt)
        self.assertIsNone(modul.pruefungsleistung.note)
        self.assertEqual(modul.pruefungsleistung.ergebnis, Pruefungsergebnis.AUSSTEHEND)

    def test_abschliessen_benoten_und_kennzahlen(self):
        fenster = self.fenster()
        liste = fenster.modulleiste.liste
        item = liste.item(0)

        def bearbeiten(dialog):
            self.assertEqual(dialog.alter_code, "MAT-1")
            self.waehlen(dialog.status, Bearbeitungsstatus.IN_BEARBEITUNG)
            self.waehlen(dialog.ergebnis, Pruefungsergebnis.BESTANDEN)
            dialog.benotet.setChecked(True)
            dialog.note.setFocus()
            QTest.keyClick(dialog.note, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
            QTest.keyClicks(dialog.note, "1,3")
            QTest.keyClick(dialog.note, Qt.Key.Key_Tab)
            dialog.ok.click()
            self.assertIsNotNone(dialog.modul)

        self.ausloesen(
            lambda: QTest.mouseClick(liste.viewport(), Qt.MouseButton.LeftButton,
                                    pos=liste.visualItemRect(item).center()),
            bearbeiten,
        )
        self.assertEqual(fenster.studiengang, laden(self.pfad))
        self.assertEqual(fenster.studiengang.erreichte_ects(), 20)
        self.assertEqual(fenster.studiengang.notendurchschnitt(), Decimal("1.75"))
        anzahl = [w.text() for w in fenster.inhalt.findChildren(QLabel) if w.property("rolle") == "anzahl"]
        self.assertEqual(anzahl, ["0", "2", "3"])
        texte = [w.text() for w in fenster.inhalt.findChildren(QLabel)]
        self.assertIn("20 / 180", texte)
        self.assertIn("Note: 1,3", texte)
        modul = fenster.studiengang.modul_finden("MAT-1")[1]
        self.assertIsInstance(modul.status, Bearbeitungsstatus)
        self.assertIsInstance(modul.pruefungsleistung.ergebnis, Pruefungsergebnis)
        neu = DashboardFenster(laden(self.pfad), self.pfad)
        self.assertEqual(neu.studiengang.modul_finden("MAT-1")[1].pruefungsleistung.note, Decimal("1.3"))

    def test_kanbankarte_oeffnen_und_umbenennen(self):
        fenster = self.fenster()
        karte = next(k for k in fenster.findChildren(ModulKarte) if k.modulcode == "OOP-PY")
        titel = next(w for w in karte.findChildren(QLabel) if w.text() == "OOP mit Python")
        self.assertTrue(titel.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

        def bearbeiten(dialog):
            self.assertEqual(dialog.alter_code, "OOP-PY")
            dialog.name.setText("Neuer Name")
            dialog.code.setText("NEUER-CODE")
            dialog.aktueller_abschnitt.setValue(3)
            dialog.ok.click()
            self.assertIsNotNone(dialog.modul)

        self.ausloesen(
            lambda: QTest.mouseClick(karte, Qt.MouseButton.LeftButton,
                                    pos=titel.mapTo(karte, titel.rect().center())),
            bearbeiten,
        )
        self.assertEqual(len(fenster.studiengang.module), 5)
        neue_karte = next(k for k in fenster.findChildren(ModulKarte) if k.modulcode == "NEUER-CODE")
        self.assertEqual(neue_karte.findChild(QProgressBar).value(), 75)
        self.assertEqual(fenster.modulleiste.liste.currentItem().data(Qt.ItemDataRole.UserRole), "NEUER-CODE")
        self.ausloesen(
            lambda: QTest.mouseClick(neue_karte, Qt.MouseButton.LeftButton),
            lambda dialog: self.assertEqual(dialog.alter_code, "NEUER-CODE"),
        )

    def test_karte_und_liste_per_tastatur(self):
        fenster = self.fenster()
        karte = next(k for k in fenster.findChildren(ModulKarte) if k.modulcode == "MAT-1")
        karte.setFocus()
        self.ausloesen(
            lambda: QTest.keyClick(karte, Qt.Key.Key_Space),
            lambda dialog: self.assertEqual(dialog.alter_code, "MAT-1"),
        )
        liste = fenster.modulleiste.liste
        liste.setCurrentRow(1)
        liste.setFocus()
        self.ausloesen(
            lambda: QTest.keyClick(liste, Qt.Key.Key_Return),
            lambda dialog: self.assertEqual(dialog.alter_code, "OOP-PY"),
        )

    def test_note_beim_zuruecksetzen_entfernen(self):
        for status in (Bearbeitungsstatus.NOCH_ZU_TUN, Bearbeitungsstatus.IN_BEARBEITUNG):
            dialog = self.dialog("PROG-1")
            self.assertEqual(dialog.note.value(), 1.7)
            self.waehlen(dialog.status, status)
            self.assertFalse(dialog.benotet.isChecked())
            self.assertFalse(dialog.note.isEnabled())
            dialog.ok.click()
            geladen = laden(self.pfad)
            modul = geladen.modul_finden("PROG-1")[1]
            self.assertIsNone(modul.pruefungsleistung.note)
            self.assertEqual(modul.pruefungsleistung.ergebnis, Pruefungsergebnis.AUSSTEHEND)
            self.assertEqual(geladen.erreichte_ects(), 5)
            self.assertEqual(geladen.notendurchschnitt(), Decimal("2.3"))

    def test_pruefungsformwechsel_und_termin_entfernen(self):
        dialog = self.dialog("OOP-PY")
        dialog.pruefungsform.setCurrentText("Klausur")
        self.assertFalse(dialog.abschnitte.isEnabled())
        self.assertFalse(dialog.aktueller_abschnitt.isEnabled())
        dialog.ok.click()
        pruefung = laden(self.pfad).modul_finden("OOP-PY")[1].pruefungsleistung
        self.assertIsInstance(pruefung, EinteiligePruefungsleistung)
        self.assertIs(pruefung.pruefungsform, Pruefungsform.KLAUSUR)
        self.assertFalse(hasattr(pruefung, "aktueller_abschnitt"))
        dialog = self.dialog("MAT-1")
        self.assertTrue(dialog.termin_festgelegt.isChecked())
        dialog.termin_festgelegt.setChecked(False)
        self.assertFalse(dialog.termin.isEnabled())
        dialog.ok.click()
        self.assertIsNone(laden(self.pfad).modul_finden("MAT-1")[1].pruefungsleistung.termin)

    def test_note_erfordert_ergebnis_und_muss_dazu_passen(self):
        dialog = self.dialog("MAT-1")
        self.waehlen(dialog.status, Bearbeitungsstatus.FERTIG)
        self.assertFalse(dialog.note.isEnabled())
        self.waehlen(dialog.ergebnis, Pruefungsergebnis.BESTANDEN)
        dialog.benotet.setChecked(True)
        dialog.note.setValue(5)
        vorher = self.pfad.read_bytes()
        dialog.ok.click()
        self.assertTrue(dialog.isVisible())
        self.assertIn("passen nicht zusammen", dialog.fehler.text())
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.waehlen(dialog.ergebnis, Pruefungsergebnis.NICHT_BESTANDEN)
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        geladen = laden(self.pfad)
        self.assertEqual(geladen.modul_finden("MAT-1")[1].pruefungsleistung.note, 5)
        self.assertEqual(geladen.erreichte_ects(), 15)

    def test_unbenotet_und_ausstehendes_ergebnis(self):
        dialog = self.dialog("PROG-1")
        dialog.benotet.setChecked(False)
        dialog.ok.click()
        geladen = laden(self.pfad)
        self.assertEqual(geladen.erreichte_ects(), 15)
        self.assertEqual(geladen.notendurchschnitt(), Decimal("2.3"))
        dialog = self.dialog("PROG-1")
        self.waehlen(dialog.ergebnis, Pruefungsergebnis.AUSSTEHEND)
        self.assertFalse(dialog.note.isEnabled())
        self.assertFalse(dialog.benotet.isChecked())
        dialog.ok.click()
        self.assertEqual(laden(self.pfad).erreichte_ects(), 5)

    def test_abbrechen_doppelter_code_und_schreibfehler(self):
        vorher = self.pfad.read_bytes()
        original = deepcopy(self.studiengang)
        dialog = self.dialog("MAT-1")
        dialog.name.setText("Nicht speichern")
        dialog.reject()
        self.assertEqual(self.pfad.read_bytes(), vorher)
        dialog = self.dialog("MAT-1")
        dialog.code.setText("PROG-1")
        dialog.ok.click()
        self.assertTrue(dialog.isVisible())
        self.assertIn("bereits vergeben", dialog.fehler.text())
        self.assertEqual(self.pfad.read_bytes(), vorher)
        dialog.code.setText("MAT-1")
        dialog.name.setText("Umbenannt")
        with patch("modul_dialog.speichern", side_effect=PermissionError("Kein Zugriff")):
            dialog.ok.click()
        self.assertTrue(dialog.isVisible())
        self.assertIsNone(dialog.modul)
        self.assertEqual(self.studiengang, original)
        self.assertEqual(self.pfad.read_bytes(), vorher)
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(len(laden(self.pfad).module), 5)
        self.assertEqual(laden(self.pfad).modul_finden("MAT-1")[1].bezeichnung, "Umbenannt")

    def test_dezimalnote_wird_nicht_gerundet(self):
        modul = self.studiengang.modul_finden("PROG-1")[1]
        modul.ects = 2
        modul.pruefungsleistung.note = Decimal("1.75")
        dialog = self.dialog("PROG-1")
        self.assertEqual(dialog.ects.value(), 2)
        self.assertEqual(dialog.note.value(), 1.75)
        dialog.ok.click()
        self.assertEqual(laden(self.pfad).modul_finden("PROG-1")[1], modul)

    def test_statuswechsel_verschieben_keine_felder(self):
        dialog = self.dialog("OOP-PY")
        felder = (dialog.name, dialog.code, dialog.semester, dialog.pruefungsform,
                  dialog.abschnitte, dialog.status, dialog.aktueller_abschnitt,
                  dialog.termin, dialog.ergebnis, dialog.note, dialog.ok)
        vorher = [(w.mapTo(dialog, QPoint()), w.size()) for w in felder]
        for status in Bearbeitungsstatus:
            self.waehlen(dialog.status, status)
            self.app.processEvents()
            self.assertEqual([(w.mapTo(dialog, QPoint()), w.size()) for w in felder], vorher)
        dialog.pruefungsform.setCurrentText("Klausur")
        self.app.processEvents()
        self.assertEqual([(w.mapTo(dialog, QPoint()), w.size()) for w in felder], vorher)

    def test_modell_weist_unpassende_angaben_zurueck(self):
        for code, aenderung in (
            ("MAT-1", lambda m: setattr(m.pruefungsleistung, "note", 2)),
            ("MAT-1", lambda m: setattr(m.pruefungsleistung, "ergebnis", Pruefungsergebnis.BESTANDEN)),
            ("OOP-PY", lambda m: setattr(m.pruefungsleistung, "aktueller_abschnitt", 5)),
            ("OOP-PY", lambda m: setattr(m, "status", Bearbeitungsstatus.NOCH_ZU_TUN)),
            ("PROG-1", lambda m: setattr(m.pruefungsleistung, "note", 5)),
        ):
            vorher = deepcopy(self.studiengang)
            semester, modul = self.studiengang.modul_finden(code)
            neu = deepcopy(modul)
            aenderung(neu)
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.studiengang.modul_aktualisieren(code, neu, semester.nummer)
            self.assertEqual(self.studiengang, vorher)


if __name__ == "__main__":
    unittest.main()
