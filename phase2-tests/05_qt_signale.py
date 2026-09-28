import os
from dataclasses import dataclass

# Der Test braucht kein sichtbares Fenster.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


@dataclass
class Modul:
    name: str


class ModulFormular(QWidget):
    def __init__(self, modul):
        super().__init__()
        self.modul = modul
        self.name = QLineEdit(modul.name)
        self.speichern = QPushButton("Speichern")
        self.anzeige = QLabel(modul.name)

        layout = QVBoxLayout(self)
        layout.addWidget(self.name)
        layout.addWidget(self.speichern)
        layout.addWidget(self.anzeige)
        self.speichern.clicked.connect(self.uebernehmen)

    def uebernehmen(self):
        name = self.name.text().strip()
        if not name:
            self.anzeige.setText("Bitte einen Namen eingeben.")
            return
        self.modul.name = name
        self.anzeige.setText(self.modul.name)


def main():
    app = QApplication([])
    modul = Modul("Python")
    formular = ModulFormular(modul)

    formular.name.setText("Datenbanken")
    formular.speichern.click()
    assert modul.name == "Datenbanken"
    assert formular.anzeige.text() == "Datenbanken"

    formular.name.setText(" ")
    formular.speichern.click()
    assert modul.name == "Datenbanken"
    assert formular.anzeige.text() == "Bitte einen Namen eingeben."

    formular.close()
    app.quit()
    print("T5: Ein Klick prüft die Eingabe, aktualisiert das Modul und erneuert die Anzeige.")


if __name__ == "__main__":
    main()
