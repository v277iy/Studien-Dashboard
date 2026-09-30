from dataclasses import fields
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

from PySide6.QtCore import QDate, QEvent
from PySide6.QtWidgets import QApplication, QDateEdit, QLabel

from dashboard import zeitplan
from einrichtung import StudiengangDialog
from modelle import (
    Bearbeitungsstatus, EinteiligePruefungsleistung, MehrteiligePruefungsleistung,
    Modul, Pruefungsform, Semester, Studiengang,
)
from speicherung import laden, speichern, studiengang_als_dict, studiengang_aus_dict


class ZeitplanungTest(unittest.TestCase):
    def test_sechs_kalendermonate_pro_semester(self):
        for start, semester, ende in (
            (date(2026, 10, 1), 6, date(2029, 10, 1)),
            (date(2026, 10, 1), 1, date(2027, 4, 1)),
            (date(2023, 8, 31), 1, date(2024, 2, 29)),
            (date(2024, 8, 31), 1, date(2025, 2, 28)),
            (date(2024, 2, 29), 2, date(2025, 2, 28)),
            (date(2023, 8, 31), 2, date(2024, 8, 31)),
            (date(2026, 4, 30), 1, date(2026, 10, 30)),
            (date(1, 1, 1), 1, date(1, 7, 1)),
            (date(9999, 6, 30), 1, date(9999, 12, 30)),
        ):
            with self.subTest(start=start, semester=semester):
                sg = Studiengang("Studium", semester, 180, start)
                self.assertEqual(sg.enddatum, ende)

    def test_enddatum_wird_aus_den_aktuellen_angaben_berechnet(self):
        sg = Studiengang("Studium", 1, 180, date(2023, 8, 31))
        self.assertEqual(sg.enddatum, date(2024, 2, 29))
        sg.regelstudienzeit = 2
        self.assertEqual(sg.enddatum, date(2024, 8, 31))
        sg.startdatum = date(2026, 10, 1)
        self.assertEqual(sg.enddatum, date(2027, 10, 1))
        with self.assertRaises(AttributeError):
            sg.enddatum = date(2030, 1, 1)

    def test_ungueltige_planung(self):
        for anzahl in (0, -1, 1.5, True, "6", None):
            with self.subTest(anzahl=anzahl), self.assertRaises(ValueError):
                Studiengang("Studium", anzahl, 180, date(2026, 10, 1))
        for start in (None, "2026-10-01", date(9999, 12, 31)):
            with self.subTest(start=start), self.assertRaises(ValueError):
                Studiengang("Studium", 6, 180, start)

    def test_resttage_und_ueberziehung(self):
        sg = Studiengang("Studium", 1, 180, date(2026, 10, 1))
        for heute, tage in (
            (date(2026, 10, 1), 182),
            (date(2027, 3, 30), 2),
            (date(2027, 3, 31), 1),
            (date(2027, 4, 1), 0),
            (date(2027, 4, 2), -1),
            (date(2027, 4, 3), -2),
        ):
            self.assertEqual(sg.verbleibende_tage(heute), tage)

    def test_nur_studiengang_speichert_startdatum(self):
        sg = Studiengang("Studium", 6, 180, date(2026, 10, 1), [Semester(1)])
        self.assertEqual({f.name for f in fields(Semester)}, {"nummer", "module"})
        self.assertNotIn("enddatum", {f.name for f in fields(Studiengang)})
        daten = studiengang_als_dict(sg)["studiengang"]
        self.assertEqual(daten["startdatum"], "2026-10-01")
        self.assertNotIn("enddatum", daten)
        self.assertEqual(daten["semester"], [{"nummer": 1, "module": []}])
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "Studiengang.json"
            speichern(pfad, sg)
            neu = laden(pfad)
            self.assertEqual(neu, sg)
            self.assertEqual(neu.enddatum, date(2029, 10, 1))

    def test_alle_pruefungsformen_im_json(self):
        for form in Pruefungsform:
            with self.subTest(form=form):
                if form.ist_mehrteilig():
                    pruefung = MehrteiligePruefungsleistung(
                        pruefungsform=form, anzahl_abschnitte=4, aktueller_abschnitt=2,
                    )
                else:
                    pruefung = EinteiligePruefungsleistung(pruefungsform=form)
                modul = Modul("A", "Modul", 5, Bearbeitungsstatus.IN_BEARBEITUNG, pruefung)
                modul.angaben_pruefen()
                sg = Studiengang("Studium", 6, 180, date(2026, 10, 1), [Semester(1, [modul])])
                daten = json.loads(json.dumps(studiengang_als_dict(sg)))
                pruefungsdaten = daten["studiengang"]["semester"][0]["module"][0]["pruefungsleistung"]
                self.assertEqual(pruefungsdaten["pruefungsform"], form.value)
                self.assertNotIn("klasse", pruefungsdaten)
                neu = studiengang_aus_dict(daten)
                self.assertEqual(neu, sg)
                self.assertIs(type(neu.module[0].pruefungsleistung), type(pruefung))
                self.assertIs(neu.module[0].pruefungsleistung.pruefungsform, form)

    def test_pruefungsform_und_abschnittsangaben_muessen_passen(self):
        pruefung = EinteiligePruefungsleistung(pruefungsform=Pruefungsform.KLAUSUR)
        modul = Modul("A", "A", 5, Bearbeitungsstatus.NOCH_ZU_TUN, pruefung)
        sg = Studiengang("Studium", 6, 180, date(2026, 10, 1), [Semester(1, [modul])])
        for feld, wert in (("anzahl_abschnitte", 4), ("aktueller_abschnitt", 1)):
            daten = studiengang_als_dict(sg)
            daten["studiengang"]["semester"][0]["module"][0]["pruefungsleistung"][feld] = wert
            with self.subTest(feld=feld), self.assertRaises(ValueError):
                studiengang_aus_dict(daten)


class ZeitplanungGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_dashboard_zeigt_berechnetes_enddatum_und_resttage(self):
        sg = Studiengang("Studium", 1, 180, date(2026, 10, 1))
        for heute, erwartet in (
            (date(2027, 3, 30), "Noch 2 Tage"),
            (date(2027, 3, 31), "Noch 1 Tag"),
            (date(2027, 4, 1), "Enddatum heute"),
            (date(2027, 4, 2), "Um 1 Tag überzogen"),
            (date(2027, 4, 3), "Um 2 Tage überzogen"),
        ):
            with self.subTest(heute=heute), patch("dashboard.date") as datum:
                datum.today.return_value = heute
                kasten = zeitplan(sg)
                texte = [w.text() for w in kasten.findChildren(QLabel)]
                self.assertIn("01.04.2027", texte)
                self.assertIn("Studienstart: 01.10.2026", texte)
                self.assertIn(erwartet, texte)
                kasten.deleteLater()

    def test_einrichtung_erfasst_nur_das_startdatum(self):
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "Studiengang.json"
            dialog = StudiengangDialog(pfad)
            self.assertEqual(dialog.findChildren(QDateEdit), [dialog.startdatum])
            dialog.name.setText("Studium")
            dialog.startdatum.setDate(QDate(2023, 8, 31))
            dialog.semester.setValue(1)
            dialog.ok.click()
            self.assertEqual(laden(pfad).enddatum, date(2024, 2, 29))

    def test_zu_spaetes_startdatum_wird_abgelehnt(self):
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "Studiengang.json"
            dialog = StudiengangDialog(pfad)
            dialog.name.setText("Studium")
            dialog.startdatum.setDate(QDate(9999, 12, 31))
            dialog.ok.click()
            self.assertIsNone(dialog.studiengang)
            self.assertIn("Enddatum", dialog.fehler.text())
            self.assertFalse(pfad.exists())


if __name__ == "__main__":
    unittest.main()
