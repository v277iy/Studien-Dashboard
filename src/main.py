import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QDialog

from dashboard import DashboardFenster
from einrichtung import StudiengangDialog
from modelle import Studiengang
from speicherung import laden


def studiengang_pfad() -> Path:
    ordner = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    return Path(ordner) / "Studiengang.json"


def studiengang_oeffnen(pfad: Path) -> Studiengang | None:
    try:
        return laden(pfad)
    except FileNotFoundError:
        hinweis = ""
    except (OSError, ValueError):
        hinweis = (
            "Studiengang.json ist ungültig oder nicht lesbar. "
            "Beim Speichern bleibt die alte Datei als .bak erhalten."
        )
    dialog = StudiengangDialog(pfad, hinweis)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.studiengang
    return None


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Studien-Dashboard")
    app.setStyleSheet(Path(__file__).with_name("style.qss").read_text(encoding="utf-8"))

    studiengang = studiengang_oeffnen(studiengang_pfad())
    if studiengang is None:
        return 0
    fenster = DashboardFenster(studiengang)

    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
