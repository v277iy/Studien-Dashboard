from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
from typing import get_type_hints
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar

from dashboard import balken, modulkarte, studienfortschritt
from modelle import (
    Bearbeitungsstatus, EinteiligePruefungsleistung, MehrteiligePruefungsleistung,
    Modul, Prozent, Pruefungsergebnis, Pruefungsform, Pruefungsleistung,
    Semester, Studiengang,
)


def studiengang(ects=1):
    pruefung = EinteiligePruefungsleistung(
        pruefungsform=Pruefungsform.KLAUSUR,
        ergebnis=Pruefungsergebnis.BESTANDEN, note=Decimal("1.7"),
    )
    modul = Modul("A", "Modul", ects, Bearbeitungsstatus.FERTIG, pruefung)
    return Studiengang("Studium", 6, 3, date(2026, 10, 1), [Semester(1, [modul])])


class ProzentTest(unittest.TestCase):
    def test_prozent_ist_ein_typname_fuer_decimal(self):
        self.assertIs(Prozent.__value__, Decimal)
        for funktion in (
            Pruefungsleistung.fortschritt,
            EinteiligePruefungsleistung.fortschritt,
            MehrteiligePruefungsleistung.fortschritt,
            Modul.fortschritt,
            Studiengang.ects_fortschritt,
        ):
            self.assertIs(get_type_hints(funktion)["return"], Prozent)
        self.assertIs(get_type_hints(balken)["wert"], Prozent)

    def test_einteilige_leistung_liefert_decimal(self):
        pruefung = EinteiligePruefungsleistung(pruefungsform=Pruefungsform.KLAUSUR)
        self.assertIsInstance(pruefung.fortschritt(), Decimal)
        self.assertEqual(pruefung.fortschritt(), Decimal(0))

    def test_mehrteilige_leistung_rechnet_mit_decimal(self):
        pruefung = MehrteiligePruefungsleistung(
            pruefungsform=Pruefungsform.PORTFOLIO, anzahl_abschnitte=3,
        )
        for abschnitt in (None, 1, 2, 3):
            pruefung.aktueller_abschnitt = abschnitt
            erwartet = Decimal(100) * (abschnitt or 0) / 3
            self.assertIsInstance(pruefung.fortschritt(), Decimal)
            self.assertEqual(pruefung.fortschritt(), erwartet)

    def test_modulfortschritt_fuer_alle_statuswerte(self):
        for status, erwartet in (
            (Bearbeitungsstatus.NOCH_ZU_TUN, Decimal(0)),
            (Bearbeitungsstatus.IN_BEARBEITUNG, Decimal(100) / 3),
            (Bearbeitungsstatus.FERTIG, Decimal(100)),
        ):
            pruefung = MehrteiligePruefungsleistung(
                pruefungsform=Pruefungsform.PORTFOLIO, anzahl_abschnitte=3,
                aktueller_abschnitt=1 if status == Bearbeitungsstatus.IN_BEARBEITUNG else None,
                ergebnis=(Pruefungsergebnis.BESTANDEN if status == Bearbeitungsstatus.FERTIG
                          else Pruefungsergebnis.AUSSTEHEND),
            )
            modul = Modul("A", "Modul", 5, status, pruefung)
            modul.angaben_pruefen()
            self.assertIsInstance(modul.fortschritt(), Decimal)
            self.assertEqual(modul.fortschritt(), erwartet)

    def test_ects_fortschritt_und_noten(self):
        for ects in (1, 2, 3, 4):
            sg = studiengang(ects)
            self.assertIsInstance(sg.ects_fortschritt(), Decimal)
            self.assertEqual(sg.ects_fortschritt(), Decimal(100) * ects / 3)
            self.assertIs(type(sg.erreichte_ects()), int)
            self.assertEqual(sg.notendurchschnitt(), Decimal("1.7"))
        sg.semester.clear()
        self.assertIsInstance(sg.ects_fortschritt(), Decimal)
        self.assertEqual(sg.ects_fortschritt(), Decimal(0))


class ProzentGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_balken_rundet_und_begrenzt_decimalwerte(self):
        self.assertEqual(balken().value(), 0)
        for wert, erwartet in (
            ("-1", 0), ("0", 0), ("12.4", 12), ("12.5", 12),
            ("12.6", 13), ("100", 100), ("120", 100),
        ):
            with self.subTest(wert=wert):
                self.assertEqual(balken(Decimal(wert)).value(), erwartet)

    def test_kennzahlen_zeigen_gerundete_prozente(self):
        kasten = studienfortschritt(studiengang())
        self.assertIn("33 %", [w.text() for w in kasten.findChildren(QLabel)])
        self.assertEqual(kasten.findChild(QProgressBar).value(), 33)

    def test_modulkarte_zeigt_decimalfortschritt(self):
        pruefung = MehrteiligePruefungsleistung(
            pruefungsform=Pruefungsform.PORTFOLIO, anzahl_abschnitte=3, aktueller_abschnitt=1,
        )
        modul = Modul("A", "Modul", 5, Bearbeitungsstatus.IN_BEARBEITUNG, pruefung)
        karte = modulkarte(modul, "aktiv")
        self.assertIn("33 %", [w.text() for w in karte.findChildren(QLabel)])
        self.assertEqual(karte.findChild(QProgressBar).value(), 33)


if __name__ == "__main__":
    unittest.main()
