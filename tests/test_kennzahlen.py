from copy import deepcopy
from datetime import date
from decimal import Decimal
import inspect
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from PySide6.QtCore import QDate, QEvent, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from dashboard import DashboardFenster
from einrichtung import StudiengangDialog
from modelle import (
    Bearbeitungsstatus,
    EinteiligePruefungsleistung,
    MehrteiligePruefungsleistung,
    Modul,
    Pruefungsform,
    Pruefungsergebnis,
    Pruefungsleistung,
    Semester,
    Studiengang,
)
from modul_dialog import ModulDialog
from speicherung import laden, speichern, studiengang_als_dict, studiengang_aus_dict


BEISPIEL = Path(__file__).with_name("daten") / "Studiengang.json"


def modul(code, status=Bearbeitungsstatus.FERTIG, ects=5, note=None):
    pruefung = EinteiligePruefungsleistung(
        pruefungsform=Pruefungsform.KLAUSUR,
        note=Decimal(note) if note is not None else None,
        ergebnis=(Pruefungsergebnis.BESTANDEN if status == Bearbeitungsstatus.FERTIG
                  else Pruefungsergebnis.AUSSTEHEND),
    )
    return Modul(code, code, ects, status, pruefung)


def studiengang(semester=None):
    return Studiengang(
        "Studium", 6, 180, date(2026, 10, 1),
        semester=semester or [], zielnote=Decimal("2.0"),
    )


class KennzahlenTest(unittest.TestCase):
    def test_nur_die_pruefungsbasis_ist_abstrakt(self):
        self.assertTrue(inspect.isabstract(Pruefungsleistung))
        with self.assertRaises(TypeError):
            Pruefungsleistung(pruefungsform=Pruefungsform.KLAUSUR)
        self.assertFalse(inspect.isabstract(EinteiligePruefungsleistung))
        self.assertFalse(inspect.isabstract(MehrteiligePruefungsleistung))
        for form in Pruefungsform:
            if form.ist_mehrteilig():
                pruefung = MehrteiligePruefungsleistung(
                    pruefungsform=form, anzahl_abschnitte=4, aktueller_abschnitt=2,
                )
                self.assertEqual(pruefung.fortschritt(), 50)
            else:
                pruefung = EinteiligePruefungsleistung(pruefungsform=form)
                self.assertEqual(pruefung.fortschritt(), 0)
            self.assertIs(pruefung.pruefungsform, form)

    def test_notenwerte_im_modell_sind_decimal(self):
        for pruefung in (
            EinteiligePruefungsleistung(pruefungsform=Pruefungsform.KLAUSUR, note=1.7),
            MehrteiligePruefungsleistung(pruefungsform=Pruefungsform.PORTFOLIO, anzahl_abschnitte=4, note=2.3),
        ):
            self.assertIsInstance(pruefung.note, Decimal)
        sg = Studiengang("Studium", 6, 180, date(2030, 9, 30), zielnote=1.7)
        self.assertEqual(sg.zielnote, Decimal("1.7"))
        self.assertIsInstance(sg.zielnote, Decimal)

    def test_semester_fertig_nur_mit_modulen(self):
        semester = Semester(1)
        self.assertFalse(semester.ist_fertig())
        semester.module = [modul("A"), modul("B")]
        self.assertTrue(semester.ist_fertig())
        semester.module[1].pruefungsleistung.ergebnis = Pruefungsergebnis.NICHT_BESTANDEN
        self.assertFalse(semester.ist_fertig())
        for status in (Bearbeitungsstatus.NOCH_ZU_TUN, Bearbeitungsstatus.IN_BEARBEITUNG):
            semester.module[1].status = status
            self.assertFalse(semester.ist_fertig())

    def test_aktuelles_semester_ist_das_frueheste_mit_offenen_modulen(self):
        sg = studiengang([
            Semester(4, [modul("D", Bearbeitungsstatus.IN_BEARBEITUNG)]),
            Semester(1),
            Semester(3, [modul("C")]),
            Semester(2, [modul("B", Bearbeitungsstatus.NOCH_ZU_TUN)]),
        ])
        self.assertEqual(sg.aktuelles_semester(), 2)
        sg.modul_finden("B")[1].status = Bearbeitungsstatus.FERTIG
        sg.modul_finden("B")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.BESTANDEN
        self.assertEqual(sg.aktuelles_semester(), 4)
        sg.modul_finden("D")[1].status = Bearbeitungsstatus.FERTIG
        sg.modul_finden("D")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.BESTANDEN
        self.assertIsNone(sg.aktuelles_semester())
        self.assertIsNone(studiengang().aktuelles_semester())

    def test_verbleibende_semester_zaehlen_alle_abgeschlossenen(self):
        sg = studiengang([
            Semester(5, [modul("E")]),
            Semester(1, [modul("A")]),
            Semester(2, [modul("B", Bearbeitungsstatus.IN_BEARBEITUNG)]),
            Semester(3),
            Semester(4, [modul("C"), modul("D", Bearbeitungsstatus.NOCH_ZU_TUN)]),
        ])
        self.assertEqual(sg.verbleibende_semester(), 4)
        sg.modul_finden("D")[1].status = Bearbeitungsstatus.FERTIG
        sg.modul_finden("D")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.BESTANDEN
        self.assertEqual(sg.verbleibende_semester(), 3)
        sg.modul_finden("B")[1].status = Bearbeitungsstatus.FERTIG
        sg.modul_finden("B")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.BESTANDEN
        self.assertEqual(sg.verbleibende_semester(), 2)
        self.assertEqual(studiengang().verbleibende_semester(), 6)
        leer = studiengang([Semester(n) for n in range(1, 7)])
        self.assertEqual(leer.verbleibende_semester(), 6)

    def test_alle_semester_fertig_und_modul_wieder_offen(self):
        sg = studiengang([Semester(n, [modul(str(n))]) for n in range(1, 7)])
        self.assertEqual(sg.verbleibende_semester(), 0)
        self.assertIsNone(sg.aktuelles_semester())
        sg.modul_finden("3")[1].status = Bearbeitungsstatus.NOCH_ZU_TUN
        self.assertEqual(sg.verbleibende_semester(), 1)
        self.assertEqual(sg.aktuelles_semester(), 3)
        sg.semester.append(Semester(7, [modul("7", Bearbeitungsstatus.NOCH_ZU_TUN)]))
        self.assertEqual(sg.verbleibende_semester(), 2)

    def test_semesterzahlen_sind_unabhaengig_von_datumswerten(self):
        sg = studiengang([
            Semester(2, [modul("B")]),
            Semester(1, [modul("A", Bearbeitungsstatus.NOCH_ZU_TUN)]),
        ])
        self.assertEqual(sg.aktuelles_semester(), 1)
        self.assertEqual(sg.verbleibende_semester(), 5)
        sg.startdatum = date(2000, 1, 1)
        self.assertEqual(sg.aktuelles_semester(), 1)
        self.assertEqual(sg.verbleibende_semester(), 5)

    def test_gewichteter_durchschnitt_mit_decimal(self):
        sg = studiengang([Semester(1, [
            modul("A", ects=1, note="1.1"),
            modul("B", ects=2, note="2.3"),
            modul("C", ects=100),
            modul("D", ects=100, note="5.0"),
        ])])
        sg.modul_finden("C")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.BESTANDEN
        sg.modul_finden("D")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.NICHT_BESTANDEN
        self.assertIsInstance(sg.notendurchschnitt(), Decimal)
        self.assertEqual(sg.notendurchschnitt(), Decimal("1.9"))
        for ziel, erwartet in (("2.0", True), ("1.9", True), ("1.8", False)):
            sg.zielnote = Decimal(ziel)
            self.assertIs(sg.zielnote_erreicht(), erwartet)

    def test_zielvergleich_ohne_rundung_und_bei_fehlenden_werten(self):
        sg = studiengang([Semester(1, [modul("A", note="2.04")])])
        self.assertEqual(sg.notendurchschnitt(), Decimal("2.04"))
        self.assertIs(sg.zielnote_erreicht(), False)
        sg.zielnote = None
        self.assertIsNone(sg.zielnote_erreicht())
        sg.zielnote = Decimal("2.0")
        sg.module[0].pruefungsleistung.note = None
        self.assertIsNone(sg.notendurchschnitt())
        self.assertIsNone(sg.zielnote_erreicht())

    def test_pruefungsform_muss_zur_gliederung_passen(self):
        for pruefung in (
            EinteiligePruefungsleistung(pruefungsform=Pruefungsform.PORTFOLIO),
            MehrteiligePruefungsleistung(pruefungsform=Pruefungsform.KLAUSUR, anzahl_abschnitte=4),
        ):
            m = Modul("A", "A", 5, Bearbeitungsstatus.NOCH_ZU_TUN, pruefung)
            with self.assertRaisesRegex(ValueError, "Gliederung"):
                m.angaben_pruefen()

    def test_datenformat_und_dezimaltexte(self):
        sg = laden(BEISPIEL)
        self.assertEqual(sg.startdatum, date(2026, 10, 1))
        self.assertIsInstance(sg.zielnote, Decimal)
        for m in sg.module:
            if m.pruefungsleistung.note is not None:
                self.assertIsInstance(m.pruefungsleistung.note, Decimal)
        sg.startdatum = date(2026, 10, 1)
        daten = studiengang_als_dict(sg)
        self.assertEqual(daten["studiengang"]["startdatum"], "2026-10-01")
        self.assertEqual(daten["studiengang"]["zielnote"], "2.0")
        self.assertEqual(studiengang_aus_dict(daten), sg)

    def test_json_zahlen_werden_ohne_float_zwischenschritt_gelesen(self):
        sg = studiengang([Semester(1, [modul("A", note="1.2345678901234567890123456789")])])
        sg.zielnote = Decimal("2.0000000000000000000000000001")
        daten = json.dumps(studiengang_als_dict(sg))
        daten = daten.replace('"1.2345678901234567890123456789"', '1.2345678901234567890123456789')
        daten = daten.replace('"2.0000000000000000000000000001"', '2.0000000000000000000000000001')
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "Studiengang.json"
            pfad.write_text(daten, encoding="utf-8")
            geladen = laden(pfad)
            self.assertEqual(geladen, sg)
            speichern(pfad, geladen)
            self.assertEqual(laden(pfad), sg)
            roh = json.loads(pfad.read_text(encoding="utf-8"))["studiengang"]
            self.assertEqual(roh["zielnote"], str(sg.zielnote))
            self.assertEqual(roh["semester"][0]["module"][0]["pruefungsleistung"]["note"], str(sg.module[0].pruefungsleistung.note))

    def test_ungueltige_dezimalnoten(self):
        for wert in ("NaN", "sNaN", "Infinity", "-Infinity", "2,0", "", True, Decimal("NaN")):
            daten = studiengang_als_dict(studiengang())
            daten["studiengang"]["zielnote"] = wert
            with self.subTest(wert=wert), self.assertRaises(ValueError):
                studiengang_aus_dict(daten)


class KennzahlenGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
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

    def test_startdatum_und_berechnetes_enddatum(self):
        dialog = StudiengangDialog(self.pfad)
        dialog.show()
        dialog.name.setText("Studium")
        self.assertFalse(hasattr(dialog, "enddatum"))
        dialog.startdatum.setDate(QDate(2028, 10, 1))
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        sg = laden(self.pfad)
        self.assertEqual(sg.startdatum, date(2028, 10, 1))
        self.assertEqual(sg.enddatum, date(2031, 10, 1))
        self.assertIsInstance(sg.zielnote, Decimal)

    def test_zielstatus_texte(self):
        for note, ziel, erwartet in (
            ("1.7", "2.0", "Zielnote erreicht"),
            ("2.0", "2.0", "Zielnote erreicht"),
            ("2.04", "2.0", "Zielnote noch nicht erreicht"),
            (None, "2.0", "Noch keine Noten"),
            ("1.7", None, "Keine Zielnote festgelegt"),
        ):
            sg = studiengang([Semester(1, [modul("A", note=note)])])
            sg.zielnote = Decimal(ziel) if ziel is not None else None
            fenster = DashboardFenster(sg, self.pfad)
            texte = [w.text() for w in fenster.inhalt.findChildren(QLabel)]
            self.assertIn(erwartet, texte)
            self.assertIn("Studienstart: 01.10.2026", texte)
            fenster.deleteLater()

    def test_semesteranzeigen_aktualisieren_sich_nach_bearbeitung(self):
        sg = laden(BEISPIEL)
        sg.modul_finden("MAT-1")[1].status = Bearbeitungsstatus.FERTIG
        sg.modul_finden("MAT-1")[1].pruefungsleistung.ergebnis = Pruefungsergebnis.BESTANDEN
        speichern(self.pfad, sg)
        fenster = DashboardFenster(sg, self.pfad)
        fenster.show()
        self.app.processEvents()
        texte = [w.text() for w in fenster.inhalt.findChildren(QLabel)]
        self.assertIn("Aktuelles Semester: 1", texte)
        self.assertIn("Noch 6 Semester", texte)
        fehler = []

        def abschliessen():
            dialog = self.app.activeModalWidget()
            try:
                self.assertIsInstance(dialog, ModulDialog)
                dialog.ergebnis.setCurrentIndex(dialog.ergebnis.findData(Pruefungsergebnis.BESTANDEN))
                dialog.ok.click()
                self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
            except BaseException as problem:
                fehler.append(problem)
                if dialog is not None:
                    dialog.reject()

        QTimer.singleShot(0, abschliessen)
        fenster.modul_bearbeiten("OOP-PY")
        if fehler:
            raise fehler[0]
        texte = [w.text() for w in fenster.inhalt.findChildren(QLabel)]
        self.assertIn("Aktuelles Semester: 2", texte)
        self.assertIn("Noch 5 Semester", texte)
        self.assertEqual(fenster.studiengang, laden(self.pfad))

    def test_unveraenderte_note_behaelt_ihre_genauigkeit_im_editor(self):
        sg = studiengang([Semester(1, [modul("A", note="1.2345678901234567890123456789")])])
        original = deepcopy(sg)
        speichern(self.pfad, sg)
        dialog = ModulDialog(sg, self.pfad, modulcode="A")
        dialog.name.setText("Neuer Name")
        dialog.ok.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(laden(self.pfad).module[0].pruefungsleistung.note, original.module[0].pruefungsleistung.note)
        self.assertEqual(sg, original)


if __name__ == "__main__":
    unittest.main()
