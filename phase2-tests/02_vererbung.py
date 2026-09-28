from abc import ABC, abstractmethod


class Pruefungsleistung(ABC):
    def __init__(self, ergebnis):
        self.ergebnis = ergebnis

    def bestanden(self):
        return self.ergebnis == "BESTANDEN"

    @abstractmethod
    def fortschritt(self):
        pass


class EinteiligePruefungsleistung(Pruefungsleistung):
    def fortschritt(self):
        if self.bestanden():
            return 100
        return 0


class MehrteiligePruefungsleistung(Pruefungsleistung):
    def __init__(self, ergebnis, anzahl_abschnitte, erledigte_abschnitte):
        super().__init__(ergebnis)
        self.anzahl_abschnitte = anzahl_abschnitte
        self.erledigte_abschnitte = erledigte_abschnitte

    def fortschritt(self):
        return 100 * self.erledigte_abschnitte / self.anzahl_abschnitte


def main():
    try:
        Pruefungsleistung("AUSSTEHEND")
    except TypeError:
        pass
    else:
        raise AssertionError("Die Basisklasse muss abstrakt sein.")

    klausur = EinteiligePruefungsleistung("BESTANDEN")
    portfolio = MehrteiligePruefungsleistung("AUSSTEHEND", 4, 2)
    assert klausur.bestanden()
    assert not portfolio.bestanden()

    fortschritte = []
    for pruefung in [klausur, portfolio]:
        fortschritte.append(pruefung.fortschritt())
    assert fortschritte == [100, 50]
    print("T2: Abstrakte Basisklasse, Vererbung und unterschiedliche Fortschrittsberechnung.")


if __name__ == "__main__":
    main()
