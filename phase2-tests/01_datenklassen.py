from dataclasses import dataclass


@dataclass
class Modul:
    ects: int
    abgeschlossen: bool = False

    def erreichte_ects(self):
        if self.abgeschlossen:
            return self.ects
        return 0


def main():
    modul = Modul(5)
    assert modul.ects == 5
    assert modul == Modul(5)
    assert modul.erreichte_ects() == 0

    modul.abgeschlossen = True
    assert modul.erreichte_ects() == 5

    modul.ects = "fünf"
    assert modul.ects == "fünf"
    print("T1: Datenklasse, eigene Methode und keine automatische Typprüfung.")


if __name__ == "__main__":
    main()
