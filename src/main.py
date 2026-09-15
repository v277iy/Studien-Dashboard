"""Minimales Hello World für das Studien-Dashboard."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


def main() -> int:
    app = QApplication(sys.argv)

    fenster = QMainWindow()
    fenster.setWindowTitle("Studien-Dashboard")
    fenster.resize(400, 240)

    text = QLabel("Hello World")
    text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    fenster.setCentralWidget(text)

    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
