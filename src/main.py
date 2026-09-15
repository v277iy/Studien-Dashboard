import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from dashboard import DashboardFenster


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(Path(__file__).with_name("style.qss").read_text(encoding="utf-8"))

    fenster = DashboardFenster()

    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
