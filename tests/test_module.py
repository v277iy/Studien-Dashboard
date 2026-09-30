from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QProgressBar, QSpinBox

from dashboard import DashboardFenster, modulkarte
from modelle import Bearbeitungsstatus, MehrteiligePruefungsleistung, Pruefungsform, Semester, Studiengang
from modul_dialog import ModulDialog
from speicherung import laden, speichern


BEISPIEL = Path(__file__).with_name("daten") / "Studiengang.json"


class ModulTest(unittest.TestCase):
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

    def fenster_oeffnen(self):
        fenster = DashboardFenster(self.studiengang, self.pfad)
        fenster.show()
        self.app.processEvents()
        return fenster

    def ausfuellen(self, dialog, pruefungsform="Klausur", semesternummer=4):
        dialog.name.setText("  Neues Modul  ")
        dialog.code.setText("  NEU-1  ")
        dialog.ects.setValue(3)
        dialog.semester.setCurrentIndex(dialog.semester.findData(semesternummer))
        dialog.pruefungsform.setCurrentText(pruefungsform)
        dialog.abschnitte.setValue(4)

    def ueber_knopf(self, fenster, aktion):
        fehler = []

        def eingeben():
            dialog = self.app.activeModalWidget()
            try:
                self.assertIsInstance(dialog, ModulDialog)
                aktion(dialog)
            except BaseException as problem:
                fehler.append(problem)
            finally:
                if dialog is not None and dialog.isVisible():
                    dialog.reject()

        QTimer.singleShot(0, eingeben)
        fenster.modulleiste.hinzufuegen.click()
        self.app.processEvents()
        if fehler:
            raise fehler[0]

    def test_liste_einklappen_und_ausklappen(self):
        fenster = self.fenster_oeffnen()
        leiste = fenster.modulleiste
        self.assertEqual(leiste.liste.count(), len(self.studiengang.module))
        self.assertTrue(leiste.hinzufuegen.isVisible())
        position = leiste.hinzufuegen.mapTo(fenster, QPoint(0, 0))
        self.assertGreater(position.y(), fenster.height() - 90)
        breite = fenster.inhalt.width()
        schalter_y = leiste.umschalter.y()
        leiste.umschalter.click()
        self.app.processEvents()
        self.assertFalse(leiste.listenbereich.isVisible())
        self.assertFalse(leiste.hinzufuegen.isVisible())
        self.assertTrue(leiste.umschalter.isVisible())
        self.assertEqual(leiste.umschalter.y(), schalter_y)
        self.assertGreater(fenster.inhalt.width(), breite)
        leiste.umschalter.click()
        self.app.processEvents()
        self.assertTrue(leiste.listenbereich.isVisible())
        self.assertTrue(leiste.hinzufuegen.isVisible())
        self.assertEqual(leiste.liste.count(), 5)

    def test_suche_nach_name_und_code(self):
        fenster = self.fenster_oeffnen()
        leiste = fenster.modulleiste
        for suchtext, code in [("  python  ", "OOP-PY"), ("mat-1", "MAT-1")]:
            leiste.suche.setText(suchtext)
            sichtbar = [
                leiste.liste.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(leiste.liste.count())
                if not leiste.liste.item(i).isHidden()
            ]
            self.assertEqual(sichtbar, [code])
        leiste.suche.setText("Unbekannt")
        self.assertTrue(leiste.leerhinweis.isVisible())
        self.assertEqual(leiste.leerhinweis.text(), "Keine Treffer")
        self.assertEqual(len(fenster.inhalt.findChildren(QFrame, "modulkarte")), 5)
        leiste.suche.clear()
        self.assertFalse(leiste.leerhinweis.isVisible())
        self.assertTrue(all(not leiste.liste.item(i).isHidden() for i in range(5)))

    def test_pflichtfelder_und_abschnittseingabe(self):
        dialog = ModulDialog(self.studiengang, self.pfad)
        dialog.show()
        self.app.processEvents()
        vorher = self.pfad.read_bytes()
        self.assertFalse(dialog.ok.isEnabled())
        dialog.name.setText("Modul")
        dialog.code.setText("   ")
        dialog.accept()
        self.assertIsNone(dialog.modul)
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.assertFalse(dialog.abschnitte.isVisible())
        dialog.code.setText("NEU-1")
        self.assertTrue(dialog.ok.isEnabled())
        self.assertIsInstance(dialog.ects, QSpinBox)
        self.assertEqual(dialog.ects.minimum(), 1)
        self.assertEqual(dialog.ects.singleStep(), 1)
        self.assertIs(type(dialog.ects.value()), int)
        for index in range(dialog.pruefungsform.count()):
            dialog.pruefungsform.setCurrentIndex(index)
            mehrteilig = Pruefungsform(dialog.pruefungsform.currentData()).ist_mehrteilig()
            self.assertEqual(dialog.abschnitte.isVisible(), mehrteilig)
        dialog.pruefungsform.setCurrentIndex(-1)
        self.assertFalse(dialog.ok.isEnabled())
        dialog.accept()
        self.assertIsNone(dialog.modul)
        dialog.pruefungsform.setCurrentIndex(0)
        dialog.semester.setCurrentIndex(-1)
        self.assertFalse(dialog.ok.isEnabled())
        dialog.accept()
        self.assertIsNone(dialog.modul)
        self.assertEqual(self.pfad.read_bytes(), vorher)

    def test_alle_pruefungsformen_speichern_und_laden(self):
        vorher = deepcopy(self.studiengang)
        for pruefungsform in ("Klausur", "Fallstudie", "Portfolio", "Projektpräsentation"):
            with self.subTest(pruefungsform=pruefungsform):
                dialog = ModulDialog(self.studiengang, self.pfad)
                self.ausfuellen(dialog, pruefungsform)
                dialog.ok.click()
                self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
                geladen = laden(self.pfad)
                modul = next(m for m in geladen.module if m.modulcode == "NEU-1")
                self.assertEqual(modul.bezeichnung, "Neues Modul")
                self.assertEqual(modul.ects, 3)
                self.assertIs(type(modul.ects), int)
                self.assertEqual(modul.status, Bearbeitungsstatus.NOCH_ZU_TUN)
                self.assertEqual(modul.fortschritt(), 0)
                self.assertIsNone(modul.pruefungsleistung.note)
                self.assertIsNone(modul.pruefungsleistung.termin)
                self.assertEqual(modul.pruefungsleistung.ergebnis, "AUSSTEHEND")
                self.assertIs(modul.pruefungsleistung.pruefungsform, Pruefungsform(pruefungsform))
                self.assertEqual(
                    isinstance(modul.pruefungsleistung, MehrteiligePruefungsleistung),
                    Pruefungsform(pruefungsform).ist_mehrteilig(),
                )
                if isinstance(modul.pruefungsleistung, MehrteiligePruefungsleistung):
                    self.assertEqual(modul.pruefungsleistung.anzahl_abschnitte, 4)
                    self.assertIsNone(modul.pruefungsleistung.aktueller_abschnitt)
                self.assertIn(modul, next(s for s in geladen.semester if s.nummer == 4).module)
                self.assertEqual([m for m in geladen.module if m.modulcode != "NEU-1"], vorher.module)
                self.assertEqual(self.studiengang, vorher)
                dialog.deleteLater()

    def test_neues_modul_erscheint_sofort_und_nach_neustart(self):
        fenster = self.fenster_oeffnen()
        fenster.modulleiste.suche.setText("Mathematik")

        def eingeben(dialog):
            self.ausfuellen(dialog, "Portfolio")
            dialog.ok.click()
            self.assertIsNotNone(dialog.modul)

        self.ueber_knopf(fenster, eingeben)
        self.assertEqual(fenster.modulleiste.suche.text(), "")
        self.assertEqual(fenster.modulleiste.liste.count(), 6)
        self.assertEqual(fenster.modulleiste.liste.currentItem().data(Qt.ItemDataRole.UserRole), "NEU-1")
        self.assertEqual(fenster.studiengang, laden(self.pfad))
        anzahl = [w.text() for w in fenster.inhalt.findChildren(QLabel) if w.property("rolle") == "anzahl"]
        self.assertEqual(anzahl, ["2", "2", "2"])
        karte = next(k for k in fenster.inhalt.findChildren(QFrame, "modulkarte") if k.toolTip() == "NEU-1")
        self.assertEqual(karte.property("status"), "offen")
        self.assertEqual(karte.findChildren(QProgressBar), [])
        texte = [w.text() for w in karte.findChildren(QLabel)]
        self.assertIn("NICHT BEGONNEN", texte)
        self.assertFalse(any("Aktueller Abschnitt" in text for text in texte))
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))["studiengang"]
        semester = next(s for s in daten["semester"] if s["nummer"] == 4)
        self.assertIs(type(semester["module"][0]["ects"]), int)
        self.assertEqual(semester["module"][0]["ects"], 3)
        self.assertIsNone(semester["module"][0]["pruefungsleistung"]["aktueller_abschnitt"])
        neu = DashboardFenster(laden(self.pfad), self.pfad)
        self.assertEqual(neu.modulleiste.liste.count(), 6)
        self.assertEqual(len(neu.inhalt.findChildren(QFrame, "modulkarte")), 6)

    def test_abbrechen_laesst_daten_unveraendert(self):
        fenster = self.fenster_oeffnen()
        vorher = self.pfad.read_bytes()

        def abbrechen(dialog):
            self.ausfuellen(dialog)
            dialog.reject()

        self.ueber_knopf(fenster, abbrechen)
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.assertIs(fenster.studiengang, self.studiengang)
        self.assertEqual(fenster.modulleiste.liste.count(), 5)

    def test_doppelter_code_auch_in_anderem_semester(self):
        dialog = ModulDialog(self.studiengang, self.pfad)
        dialog.show()
        self.ausfuellen(dialog)
        dialog.code.setText("  PROG-1  ")
        vorher = self.pfad.read_bytes()
        dialog.ok.click()
        self.assertTrue(dialog.isVisible())
        self.assertTrue(dialog.fehler.isVisible())
        self.assertIn("bereits vergeben", dialog.fehler.text())
        self.assertIsNone(dialog.modul)
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.assertEqual(len(self.studiengang.module), 5)

    def test_schreibfehler_und_erneuter_versuch(self):
        dialog = ModulDialog(self.studiengang, self.pfad)
        dialog.show()
        self.ausfuellen(dialog)
        vorher = self.pfad.read_bytes()
        with patch("modul_dialog.speichern", side_effect=PermissionError("Kein Zugriff")):
            dialog.ok.click()
        self.assertTrue(dialog.isVisible())
        self.assertTrue(dialog.fehler.isVisible())
        self.assertIn("Kein Zugriff", dialog.fehler.text())
        self.assertIsNone(dialog.modul)
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.assertEqual(len(self.studiengang.module), 5)
        self.assertEqual(dialog.code.text().strip(), "NEU-1")
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(len(laden(self.pfad).module), 6)

    def test_gewaehltes_semester_wird_bei_bedarf_angelegt(self):
        for semester in ([], [Semester(3)], [Semester(4)]):
            studiengang = Studiengang("Studium", 6, 180, date(2030, 9, 30), semester)
            vorher = deepcopy(studiengang)
            dialog = ModulDialog(studiengang, self.pfad)
            self.ausfuellen(dialog, semesternummer=4)
            dialog.ok.click()
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
            geladen = laden(self.pfad)
            gewaehlt = [s for s in geladen.semester if s.nummer == 4]
            self.assertEqual(len(gewaehlt), 1)
            self.assertEqual(len(gewaehlt[0].module), 1)
            self.assertFalse(any(s.nummer == 1 for s in geladen.semester))
            self.assertEqual(studiengang, vorher)
            dialog.deleteLater()

    def test_semesterauswahl_bis_zur_geplanten_anzahl(self):
        for anzahl in (1, 6, 8, 12):
            studiengang = deepcopy(self.studiengang)
            studiengang.regelstudienzeit = anzahl
            dialog = ModulDialog(studiengang, self.pfad)
            dialog.show()
            self.app.processEvents()
            self.assertEqual(dialog.semester.count(), anzahl)
            self.assertEqual(
                [dialog.semester.itemData(i) for i in range(anzahl)],
                list(range(1, anzahl + 1)),
            )
            self.assertEqual(
                [dialog.semester.itemText(i) for i in range(anzahl)],
                [str(nummer) for nummer in range(1, anzahl + 1)],
            )
            self.ausfuellen(dialog, semesternummer=1)
            dialog.semester.setFocus()
            QTest.keyClick(dialog.semester, Qt.Key.Key_Home)
            self.assertEqual(dialog.semester.currentData(), 1)
            for nummer in range(2, anzahl + 1):
                QTest.keyClick(dialog.semester, Qt.Key.Key_Down)
                self.assertEqual(dialog.semester.currentData(), nummer)
            QTest.keyClick(dialog.semester, Qt.Key.Key_Down)
            self.assertEqual(dialog.semester.currentData(), anzahl)
            QTest.mouseClick(dialog.ok, Qt.MouseButton.LeftButton)
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
            semester = next(s for s in laden(self.pfad).semester if s.nummer == anzahl)
            self.assertTrue(any(m.modulcode == "NEU-1" for m in semester.module))
            dialog.deleteLater()

    def test_semester_per_maus_auswaehlen_und_speichern(self):
        dialog = ModulDialog(self.studiengang, self.pfad)
        self.ausfuellen(dialog, semesternummer=1)
        dialog.show()
        self.app.processEvents()
        QTest.mouseClick(dialog.semester, Qt.MouseButton.LeftButton)
        QTest.qWait(self.app.doubleClickInterval() + 50)
        liste = dialog.semester.view()
        self.assertTrue(liste.isVisible())
        index = dialog.semester.model().index(4, 0)
        liste.scrollTo(index)
        self.app.processEvents()
        QTest.mouseClick(
            liste.viewport(), Qt.MouseButton.LeftButton, pos=liste.visualRect(index).center()
        )
        self.assertEqual(dialog.semester.currentData(), 5)
        QTest.mouseClick(dialog.ok, Qt.MouseButton.LeftButton)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        gespeichert = laden(self.pfad)
        semester = next(s for s in gespeichert.semester if s.nummer == 5)
        self.assertEqual([m.modulcode for m in semester.module], ["NEU-1"])

    def test_ungueltiges_semester_aendert_keine_daten(self):
        vorher = deepcopy(self.studiengang)
        modul = deepcopy(self.studiengang.module[0])
        modul.modulcode = "NEU-1"
        for nummer in (0, -1, self.studiengang.regelstudienzeit + 1, True, 1.5, "2", None):
            with self.subTest(nummer=nummer), self.assertRaises(ValueError):
                self.studiengang.modul_hinzufuegen(modul, nummer)
            self.assertEqual(self.studiengang, vorher)

    def test_ects_muessen_positive_ganzzahlen_sein(self):
        vorher = deepcopy(self.studiengang)
        for ects in (0, -1, True, None, "5", 2.5, 5.0):
            modul = deepcopy(self.studiengang.module[0])
            modul.modulcode = "NEU-1"
            modul.ects = ects
            with self.subTest(ects=ects):
                with self.assertRaisesRegex(ValueError, "ECTS"):
                    self.studiengang.modul_hinzufuegen(modul, 1)
                with self.assertRaisesRegex(ValueError, "ECTS"):
                    self.studiengang.modul_aktualisieren("MAT-1", modul, 1)
                self.assertEqual(self.studiengang, vorher)

    def test_formular_bleibt_beim_wechsel_an_gleicher_stelle(self):
        dialog = ModulDialog(self.studiengang, self.pfad)
        dialog.show()
        self.app.processEvents()
        felder = (
            dialog.name, dialog.code, dialog.ects, dialog.semester,
            dialog.pruefungsform, dialog.abschnitte, dialog.abschnitt_label, dialog.ok,
        )
        for groesse in (dialog.size(), dialog.minimumSizeHint()):
            dialog.resize(groesse)
            self.app.processEvents()
            vorher = [(w.mapTo(dialog, QPoint(0, 0)), w.size()) for w in felder]
            minimum = dialog.minimumSizeHint()
            for art in ("Portfolio", "Projektpräsentation", "Klausur", "Fallstudie"):
                dialog.pruefungsform.setCurrentText(art)
                self.app.processEvents()
                with self.subTest(groesse=groesse, art=art):
                    self.assertEqual(dialog.size(), groesse)
                    self.assertEqual(dialog.minimumSizeHint(), minimum)
                    self.assertEqual(
                        [(w.mapTo(dialog, QPoint(0, 0)), w.size()) for w in felder], vorher
                    )

    def test_abschnitt_und_fortschritt_nur_in_bearbeitung(self):
        for art in ("Portfolio", "Projektpräsentation"):
            dialog = ModulDialog(self.studiengang, self.pfad)
            self.ausfuellen(dialog, art)
            dialog.ok.click()
            modul = dialog.modul
            self.assertEqual(modul.status, Bearbeitungsstatus.NOCH_ZU_TUN)
            self.assertIsNone(modul.pruefungsleistung.aktueller_abschnitt)
            for status, stil, abschnitt in (
                (Bearbeitungsstatus.NOCH_ZU_TUN, "offen", None),
                (Bearbeitungsstatus.IN_BEARBEITUNG, "aktiv", 2),
                (Bearbeitungsstatus.FERTIG, "fertig", 4),
            ):
                modul.status = status
                modul.pruefungsleistung.aktueller_abschnitt = abschnitt
                karte = modulkarte(modul, stil)
                texte = [w.text() for w in karte.findChildren(QLabel)]
                balken = karte.findChildren(QProgressBar)
                if status == Bearbeitungsstatus.IN_BEARBEITUNG:
                    self.assertIn("Aktueller Abschnitt: 2 von 4", texte)
                    self.assertEqual([b.value() for b in balken], [50])
                else:
                    self.assertFalse(any("Aktueller Abschnitt" in text for text in texte))
                    self.assertEqual(balken, [])
                if status == Bearbeitungsstatus.NOCH_ZU_TUN:
                    self.assertIn("NICHT BEGONNEN", texte)
                karte.deleteLater()
            dialog.deleteLater()

    def test_namen_in_der_liste_bleiben_klartext(self):
        self.studiengang.module[0].bezeichnung = "<b>Modul</b>"
        fenster = self.fenster_oeffnen()
        item = fenster.modulleiste.liste.item(0)
        self.assertIn("&lt;b&gt;Modul&lt;/b&gt;", item.toolTip())
        zeile = fenster.modulleiste.liste.itemWidget(item)
        for text in zeile.findChildren(QLabel):
            self.assertEqual(text.textFormat(), Qt.TextFormat.PlainText)


if __name__ == "__main__":
    unittest.main()
