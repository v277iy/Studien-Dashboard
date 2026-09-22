"""Minimaler PySide6-Prototyp eines anklickbaren Kanban-Boards."""

from __future__ import annotations

import argparse
import os
from enum import StrEnum


class Pruefungsform(StrEnum):
    KLAUSUR = "Klausur"
    FALLSTUDIE = "Fallstudie"
    PORTFOLIO = "Portfolio"
    PROJEKTPRAESENTATION = "Projektpräsentation"


def argumente_lesen() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="führt den Oberflächentest ohne sichtbares Fenster aus",
    )
    return parser.parse_args()


def main() -> None:
    argumente = argumente_lesen()
    if argumente.smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    class KanbanFenster(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Machbarkeitstest: Studien-Dashboard")
            self.resize(900, 420)

            zentral = QWidget()
            hauptlayout = QVBoxLayout(zentral)
            self.auswahl = QLabel("Noch kein Modul ausgewählt")
            hauptlayout.addWidget(self.auswahl)

            board = QHBoxLayout()
            self.spalten: list[QFrame] = []
            self.karten: list[QPushButton] = []
            module = {
                "Noch zu tun": [("Mathematik II", Pruefungsform.KLAUSUR)],
                "In Bearbeitung": [("OOP mit Python", Pruefungsform.PORTFOLIO)],
                "Fertig": [("Programmierung I", Pruefungsform.KLAUSUR)],
            }

            for status, moduleintraege in module.items():
                spalte = QFrame()
                spaltenlayout = QVBoxLayout(spalte)
                spaltenlayout.addWidget(QLabel(status))
                for modulname, pruefungsform in moduleintraege:
                    name_der_form = pruefungsform.value
                    karte = QPushButton(f"{modulname}\n{name_der_form}")
                    karte.clicked.connect(
                        lambda _checked=False, name=modulname, form=name_der_form: (
                            self.auswahl.setText(f"Ausgewählt: {name} ({form})")
                        )
                    )
                    spaltenlayout.addWidget(karte)
                    self.karten.append(karte)
                spaltenlayout.addStretch()
                board.addWidget(spalte)
                self.spalten.append(spalte)

            hauptlayout.addLayout(board)
            self.setCentralWidget(zentral)

    app = QApplication([])
    fenster = KanbanFenster()
    assert len(fenster.spalten) == 3
    assert len(fenster.karten) == 3
    assert "Klausur" in fenster.karten[0].text()
    fenster.karten[0].click()
    assert fenster.auswahl.text() == "Ausgewählt: Mathematik II (Klausur)"
    print("GUI-Test erfolgreich: Modulkarten zeigen die Prüfungsform aus dem Enum an")

    fenster.show()
    if argumente.smoke_test:
        QTimer.singleShot(0, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
