from html import escape

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from modelle import Bearbeitungsstatus, Modul


STATUS_ANZEIGE = {
    Bearbeitungsstatus.NOCH_ZU_TUN: ("Noch zu tun", "offen"),
    Bearbeitungsstatus.IN_BEARBEITUNG: ("In Bearbeitung", "aktiv"),
    Bearbeitungsstatus.FERTIG: ("Fertig", "fertig"),
}


class Modulleiste(QFrame):
    neues_modul = Signal()
    modul_gewaehlt = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("modulleiste")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(20)

        kopf = QHBoxLayout()
        kopf.setSpacing(12)
        self.umschalter = QToolButton()
        self.umschalter.setObjectName("listenSchalter")
        self.umschalter.setText("☰")
        self.umschalter.setFixedSize(42, 42)
        self.umschalter.setCheckable(True)
        self.umschalter.setChecked(True)
        self.umschalter.setAccessibleName("Modulliste ein- oder ausklappen")
        kopf.addWidget(self.umschalter)
        self.titel = QLabel("Alle Module")
        self.titel.setTextFormat(Qt.TextFormat.PlainText)
        self.titel.setProperty("rolle", "boardTitel")
        kopf.addWidget(self.titel, 1)
        layout.addLayout(kopf)

        self.listenbereich = QWidget()
        inhalt = QVBoxLayout(self.listenbereich)
        inhalt.setContentsMargins(0, 0, 0, 0)
        inhalt.setSpacing(16)
        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Modul suchen …")
        self.suche.setClearButtonEnabled(True)
        inhalt.addWidget(self.suche)
        self.leerhinweis = QLabel()
        self.leerhinweis.setTextFormat(Qt.TextFormat.PlainText)
        self.leerhinweis.setProperty("rolle", "muted")
        inhalt.addWidget(self.leerhinweis)
        self.liste = QListWidget()
        self.liste.setObjectName("modulliste")
        self.liste.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.liste.setSpacing(3)
        self.liste.itemClicked.connect(
            lambda item: self.modul_gewaehlt.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        self.liste.installEventFilter(self)
        inhalt.addWidget(self.liste, 1)
        trenner = QFrame()
        trenner.setObjectName("trenner")
        trenner.setFixedHeight(1)
        inhalt.addWidget(trenner)
        self.hinzufuegen = QPushButton("+ Modul hinzufügen")
        self.hinzufuegen.setObjectName("modulHinzufuegen")
        self.hinzufuegen.clicked.connect(lambda: self.neues_modul.emit())
        inhalt.addWidget(self.hinzufuegen)
        layout.addWidget(self.listenbereich, 1)
        layout.addStretch()

        self.umschalter.toggled.connect(self.umklappen)
        self.suche.textChanged.connect(self.filtern)
        self.umklappen(True)

    def eventFilter(self, objekt, event) -> bool:
        if objekt is self.liste and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not event.isAutoRepeat():
                    self.aktuelles_modul_oeffnen()
                return True
        return super().eventFilter(objekt, event)

    def aktuelles_modul_oeffnen(self) -> None:
        item = self.liste.currentItem()
        if item is not None:
            self.modul_gewaehlt.emit(item.data(Qt.ItemDataRole.UserRole))

    def umklappen(self, ausgeklappt: bool) -> None:
        self.titel.setVisible(ausgeklappt)
        self.listenbereich.setVisible(ausgeklappt)
        self.setFixedWidth(255 if ausgeklappt else 75)
        aktion = "einklappen" if ausgeklappt else "ausklappen"
        self.umschalter.setToolTip(f"Modulliste {aktion}")

    def anzeigen(self, module: list[Modul]) -> None:
        self.liste.clear()
        for modul in module:
            status, stil = STATUS_ANZEIGE[modul.status]
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.AccessibleTextRole,
                         f"{modul.bezeichnung}, {modul.modulcode}, {status}")
            item.setToolTip(f"{escape(modul.bezeichnung)}<br>{escape(modul.modulcode)}")
            item.setData(Qt.ItemDataRole.UserRole, modul.modulcode)
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         f"{modul.bezeichnung} {modul.modulcode}".casefold())
            item.setSizeHint(QSize(0, 56))
            self.liste.addItem(item)

            zeile = QWidget()
            zeile.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            zeilenlayout = QHBoxLayout(zeile)
            zeilenlayout.setContentsMargins(10, 6, 6, 6)
            zeilenlayout.setSpacing(10)
            punkt = QFrame()
            punkt.setObjectName("listenPunkt")
            punkt.setProperty("status", stil)
            punkt.setFixedSize(10, 10)
            zeilenlayout.addWidget(punkt)
            texte = QVBoxLayout()
            texte.setSpacing(2)
            for text, rolle in ((modul.bezeichnung, "listenTitel"), (status, "klein")):
                feld = QLabel(text)
                feld.setTextFormat(Qt.TextFormat.PlainText)
                feld.setProperty("rolle", rolle)
                feld.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                texte.addWidget(feld)
            zeilenlayout.addLayout(texte, 1)
            self.liste.setItemWidget(item, zeile)
        self.filtern()

    def filtern(self) -> None:
        suchtext = self.suche.text().strip().casefold()
        sichtbar = 0
        for index in range(self.liste.count()):
            item = self.liste.item(index)
            passt = suchtext in item.data(Qt.ItemDataRole.UserRole + 1)
            item.setHidden(not passt)
            sichtbar += passt
        self.leerhinweis.setText("Keine Treffer" if suchtext else "Noch keine Module")
        self.leerhinweis.setVisible(sichtbar == 0)

    def auswaehlen(self, modulcode: str) -> None:
        self.suche.clear()
        for index in range(self.liste.count()):
            item = self.liste.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == modulcode:
                self.liste.setCurrentItem(item)
                self.liste.scrollToItem(item)
                break
