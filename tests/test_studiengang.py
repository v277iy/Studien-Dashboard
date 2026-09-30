import copy
from datetime import date
from decimal import Decimal
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

from PySide6.QtCore import QDate, QEvent, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QProgressBar, QScrollArea

from dashboard import DashboardFenster
from einrichtung import StudiengangDialog
from main import studiengang_oeffnen, studiengang_pfad
from modelle import (
    Bearbeitungsstatus, EinteiligePruefungsleistung, Modul,
    Pruefungsergebnis, Pruefungsform, Studiengang,
)
from speicherung import laden, speichern, studiengang_aus_dict


BEISPIEL = Path(__file__).with_name("daten") / "Studiengang.json"


class SpeicherungTest(unittest.TestCase):
    def setUp(self):
        self.ordner = TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.pfad = Path(self.ordner.name) / "config" / "Studiengang.json"
        self.daten = json.loads(BEISPIEL.read_text(encoding="utf-8"))

    def test_rundlauf_mit_modulen(self):
        studiengang = studiengang_aus_dict(self.daten)
        speichern(self.pfad, studiengang)
        geladen = laden(self.pfad)
        self.assertEqual(geladen, studiengang)
        for modul in geladen.module:
            self.assertIs(type(modul.ects), int)
        self.assertEqual(len(studiengang.module), 5)
        self.assertEqual(studiengang.module[1].fortschritt(), 50)
        self.assertEqual(studiengang.erreichte_ects(), 15)
        self.assertIs(type(studiengang.erreichte_ects()), int)
        self.assertEqual(studiengang.notendurchschnitt(), Decimal("1.9"))

    def test_float_ects_werden_abgelehnt(self):
        for ects in (2.5, 5.0):
            with self.subTest(ects=ects):
                studiengang = studiengang_aus_dict(self.daten)
                speichern(self.pfad, studiengang)
                vorher = self.pfad.read_bytes()
                studiengang.module[0].ects = ects
                with self.assertRaisesRegex(ValueError, "Modul-ECTS"):
                    speichern(self.pfad, studiengang)
                self.assertEqual(self.pfad.read_bytes(), vorher)
                daten = copy.deepcopy(self.daten)
                daten["studiengang"]["semester"][0]["module"][0]["ects"] = ects
                self.pfad.write_text(json.dumps(daten), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Modul-ECTS"):
                    laden(self.pfad)

    def test_bestanden_ohne_note(self):
        studiengang = studiengang_aus_dict(self.daten)
        studiengang.semester[0].module.append(Modul(
            "OHNE-NOTE", "Unbenotetes Modul", 5, Bearbeitungsstatus.FERTIG,
            EinteiligePruefungsleistung(
                pruefungsform=Pruefungsform.KLAUSUR, ergebnis=Pruefungsergebnis.BESTANDEN,
            ),
        ))
        self.assertEqual(studiengang.erreichte_ects(), 20)
        self.assertEqual(studiengang.notendurchschnitt(), Decimal("1.9"))

    def test_minimaler_studiengang_auch_mit_vergangenem_enddatum(self):
        daten = {"studiengang": {
            "bezeichnung": "Studium", "regelstudienzeit": 6,
            "gesamt_ects": 180, "startdatum": "2017-03-01",
        }}
        studiengang = studiengang_aus_dict(daten)
        self.assertEqual(studiengang.module, [])
        self.assertEqual(studiengang.erreichte_ects(), 0)
        self.assertIs(type(studiengang.erreichte_ects()), int)
        self.assertIsNone(studiengang.notendurchschnitt())
        self.assertIsNone(studiengang.zielnote)

    def test_falsche_struktur(self):
        for daten in [None, [], 42, "Text", {}, {"studiengang": []}]:
            with self.subTest(daten=daten), self.assertRaises(ValueError):
                studiengang_aus_dict(daten)

    def test_falsche_studiengangfelder(self):
        falsch = {
            "bezeichnung": [None, "", "   ", 123],
            "regelstudienzeit": [None, 0, -1, 2.5, True, "6", 10**400],
            "gesamt_ects": [None, 0, -180, 180.0, False, "180"],
            "zielnote": [True, "zwei", "2,0", 0.5, 6, float("nan"), float("inf")],
            "startdatum": [None, "", "2027-02-29", "01.10.2026", "20261001", 1, "9999-12-31"],
            "semester": [None, {}, "Semester"],
        }
        for feld, werte in falsch.items():
            for wert in werte:
                with self.subTest(feld=feld, wert=wert), self.assertRaises(ValueError):
                    daten = copy.deepcopy(self.daten)
                    daten["studiengang"][feld] = wert
                    studiengang_aus_dict(daten)
        for feld in ("bezeichnung", "regelstudienzeit", "gesamt_ects", "startdatum"):
            with self.subTest(fehlt=feld), self.assertRaises(ValueError):
                daten = copy.deepcopy(self.daten)
                del daten["studiengang"][feld]
                studiengang_aus_dict(daten)

    def test_falsche_module_werden_nicht_verschluckt(self):
        for feld, wert in [
            ("status", "UNBEKANNT"), ("ects", True), ("ects", 0), ("ects", -1),
            ("ects", 2.5), ("ects", 5.0), ("ects", "5"), ("ects", Decimal("5")),
            ("ects", float("nan")), ("ects", 10**400),
            ("modulcode", ""), ("bezeichnung", None), ("pruefungsleistung", {}),
        ]:
            with self.subTest(feld=feld, wert=wert), self.assertRaises(ValueError):
                daten = copy.deepcopy(self.daten)
                daten["studiengang"]["semester"][0]["module"][0][feld] = wert
                studiengang_aus_dict(daten)
        for feld, wert in [
            ("pruefungsform", "Unbekannt"), ("anzahl_abschnitte", 0),
            ("aktueller_abschnitt", 5), ("aktueller_abschnitt", True),
            ("note", 6), ("ergebnis", "FERTIG"), ("termin", "falsch"),
        ]:
            with self.subTest(feld=feld, wert=wert), self.assertRaises(ValueError):
                daten = copy.deepcopy(self.daten)
                pruefung = daten["studiengang"]["semester"][0]["module"][1]["pruefungsleistung"]
                pruefung[feld] = wert
                studiengang_aus_dict(daten)

    def test_doppelte_semester_und_modulcodes(self):
        daten = copy.deepcopy(self.daten)
        daten["studiengang"]["semester"].append(daten["studiengang"]["semester"][0])
        with self.assertRaises(ValueError):
            studiengang_aus_dict(daten)
        daten = copy.deepcopy(self.daten)
        daten["studiengang"]["semester"][1]["module"][0]["modulcode"] = "MAT-1"
        with self.assertRaises(ValueError):
            studiengang_aus_dict(daten)

    def test_ungueltiges_json_und_utf8(self):
        self.pfad.parent.mkdir()
        for inhalt in [b"", b"{kaputt", b"\xff"]:
            self.pfad.write_bytes(inhalt)
            with self.subTest(inhalt=inhalt), self.assertRaises(ValueError):
                laden(self.pfad)
        self.pfad.write_text(json.dumps(self.daten), encoding="utf-8-sig")
        self.assertEqual(len(laden(self.pfad).module), 5)

    def test_sicherung_wird_nicht_ueberschrieben(self):
        self.pfad.parent.mkdir()
        self.pfad.write_bytes(b"kaputt")
        sicherung = self.pfad.with_name("Studiengang.json.bak")
        sicherung.write_bytes(b"alte Sicherung")
        speichern(self.pfad, studiengang_aus_dict(self.daten), sichern=True)
        self.assertEqual(sicherung.read_bytes(), b"alte Sicherung")
        self.assertEqual(self.pfad.with_name("Studiengang.json.1.bak").read_bytes(), b"kaputt")
        self.assertEqual(len(laden(self.pfad).module), 5)

    def test_schreibfehler_laesst_alte_datei_stehen(self):
        speichern(self.pfad, studiengang_aus_dict(self.daten))
        vorher = self.pfad.read_bytes()
        with patch("speicherung.Path.replace", side_effect=PermissionError("Gesperrt")):
            with self.assertRaises(PermissionError):
                speichern(self.pfad, studiengang_aus_dict(self.daten))
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.assertEqual(list(self.pfad.parent.glob("*.tmp")), [])


class GuiTest(unittest.TestCase):
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

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def oeffnen(self, aktion):
        fehler = []

        def eingeben():
            dialog = self.app.activeModalWidget()
            try:
                self.assertIsInstance(dialog, StudiengangDialog)
                aktion(dialog)
            except BaseException as problem:
                fehler.append(problem)
                if dialog is not None:
                    dialog.reject()

        QTimer.singleShot(0, eingeben)
        ergebnis = studiengang_oeffnen(self.pfad)
        if fehler:
            raise fehler[0]
        return ergebnis

    def ausfuellen(self, dialog):
        self.assertFalse(dialog.ok.isEnabled())
        dialog.name.setText("   ")
        self.assertFalse(dialog.ok.isEnabled())
        dialog.name.setText("  Mein Studium  ")
        dialog.semester.setValue(8)
        dialog.ects.setValue(240)
        dialog.zielnote.setFocus()
        QTest.keyClick(dialog.zielnote, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(dialog.zielnote, "1,7")
        QTest.keyClick(dialog.zielnote, Qt.Key.Key_Tab)
        dialog.startdatum.setDate(QDate(2026, 10, 1))
        dialog.ok.click()

    def test_neuanlage_und_leeres_dashboard(self):
        studiengang = self.oeffnen(self.ausfuellen)
        self.assertEqual(studiengang, laden(self.pfad))
        self.assertEqual(studiengang.bezeichnung, "Mein Studium")
        self.assertEqual(studiengang.regelstudienzeit, 8)
        self.assertEqual(studiengang.gesamt_ects, 240)
        self.assertEqual(studiengang.enddatum, date(2030, 10, 1))
        self.assertEqual(studiengang.startdatum, date(2026, 10, 1))
        self.assertEqual(studiengang.zielnote, Decimal("1.7"))
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertEqual(daten["studiengang"]["zielnote"], "1.7")
        self.assertEqual(daten["studiengang"]["startdatum"], "2026-10-01")
        self.assertEqual(studiengang.module, [])
        fenster = DashboardFenster(studiengang, self.pfad)
        fenster.show()
        self.app.processEvents()
        self.assertEqual(fenster.findChildren(QFrame, "modulkarte"), [])
        texte = [widget.text() for widget in fenster.findChildren(QLabel)]
        self.assertIn("0 / 240", texte)
        self.assertIn("01.10.2030", texte)
        self.assertIn("Studienstart: 01.10.2026", texte)
        self.assertIn("Keine offenen Module", texte)
        self.assertIn("Noch 8 Semester", texte)
        self.assertIn("Noch keine Noten", texte)
        self.assertIn("8 Semester · 240 ECTS · Zielnote 1,7", texte)
        self.assertIn("Ziel: 1,7", texte)
        self.assertEqual(texte.count("Keine Module"), 3)

    def test_zielnote_vorgabe_schritte_und_grenzen(self):
        dialog = StudiengangDialog(self.pfad)
        self.assertEqual(dialog.zielnote.value(), 2.0)
        self.assertEqual(dialog.zielnote.text(), "2,0")
        self.assertEqual(dialog.zielnote.decimals(), 1)
        self.assertEqual(dialog.zielnote.minimum(), 1.0)
        self.assertEqual(dialog.zielnote.maximum(), 5.0)
        self.assertEqual(dialog.zielnote.singleStep(), 0.1)
        dialog.zielnote.stepUp()
        self.assertAlmostEqual(dialog.zielnote.value(), 2.1)
        dialog.zielnote.setValue(0)
        self.assertEqual(dialog.zielnote.value(), 1.0)
        dialog.zielnote.setValue(6)
        self.assertEqual(dialog.zielnote.value(), 5.0)
        dialog.zielnote.setValue(2.0)
        dialog.name.setText("Studium")
        dialog.ok.click()
        self.assertEqual(laden(self.pfad).zielnote, Decimal("2.0"))

    def test_ungueltige_datei_oeffnet_eingabe(self):
        self.pfad.write_bytes(b"{kaputt")
        studiengang = self.oeffnen(self.ausfuellen)
        self.assertEqual(laden(self.pfad), studiengang)
        self.assertEqual(self.pfad.with_name("Studiengang.json.bak").read_bytes(), b"{kaputt")

    def test_abbrechen_aendert_nichts(self):
        self.assertIsNone(self.oeffnen(lambda dialog: dialog.reject()))
        self.assertFalse(self.pfad.exists())
        self.pfad.write_bytes(b"kaputt")
        self.assertIsNone(self.oeffnen(lambda dialog: dialog.reject()))
        self.assertEqual(self.pfad.read_bytes(), b"kaputt")
        self.assertFalse(self.pfad.with_name("Studiengang.json.bak").exists())

    def test_gueltige_datei_ohne_dialog(self):
        self.pfad.write_bytes(BEISPIEL.read_bytes())
        vorher = self.pfad.read_bytes()
        with patch("main.StudiengangDialog", side_effect=AssertionError("Unerwartete Eingabe")):
            studiengang = studiengang_oeffnen(self.pfad)
        self.assertEqual(len(studiengang.module), 5)
        self.assertEqual(self.pfad.read_bytes(), vorher)

    def test_schreibfehler_bleibt_im_formular(self):
        dialog = StudiengangDialog(self.pfad)
        dialog.show()
        self.app.processEvents()
        with patch("einrichtung.speichern", side_effect=PermissionError("Kein Zugriff")):
            self.ausfuellen(dialog)
        self.assertIsNone(dialog.studiengang)
        self.assertTrue(dialog.isVisible())
        self.assertTrue(dialog.fehler.isVisible())
        self.assertIn("Kein Zugriff", dialog.fehler.text())
        self.assertEqual(dialog.name.text().strip(), "Mein Studium")
        self.assertEqual(dialog.zielnote.value(), 1.7)
        self.assertFalse(self.pfad.exists())

    def test_module_kennzahlen_und_scrollen(self):
        studiengang = laden(BEISPIEL)
        fenster = DashboardFenster(studiengang, self.pfad)
        fenster.resize(960, 600)
        fenster.show()
        self.app.processEvents()
        karten = fenster.findChildren(QFrame, "modulkarte")
        self.assertEqual([k.property("status") for k in karten], ["offen", "aktiv", "aktiv", "fertig", "fertig"])
        texte = [widget.text() for widget in fenster.findChildren(QLabel)]
        self.assertIn("15 / 180", texte)
        self.assertIn("1,9", texte)
        self.assertIn("165 ECTS noch offen", texte)
        for modul in studiengang.module:
            self.assertIn(modul.bezeichnung, texte)
        balken = fenster.findChildren(QProgressBar)
        self.assertIn(50, [b.value() for b in balken])
        anzahl = [w.text() for w in fenster.findChildren(QLabel) if w.property("rolle") == "anzahl"]
        self.assertEqual(anzahl, ["1", "2", "2"])
        scroll = fenster.findChild(QScrollArea)
        self.assertGreater(scroll.horizontalScrollBar().maximum(), 0)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)

    def test_namen_sind_kein_html(self):
        studiengang = laden(BEISPIEL)
        studiengang.bezeichnung = "<b>Studium</b>"
        studiengang.module[0].bezeichnung = "<h1>Modul</h1>"
        fenster = DashboardFenster(studiengang, self.pfad)
        for widget in fenster.findChildren(QLabel):
            self.assertEqual(widget.textFormat(), Qt.TextFormat.PlainText)

    @unittest.skipUnless(sys.platform.startswith("linux"), "XDG nur unter Linux")
    def test_xdg_pfad(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": self.ordner.name}):
            self.assertEqual(studiengang_pfad(), Path(self.ordner.name) / "Studien-Dashboard" / "Studiengang.json")
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": ""}):
            self.assertEqual(studiengang_pfad(), Path.home() / ".config" / "Studien-Dashboard" / "Studiengang.json")


if __name__ == "__main__":
    unittest.main()
