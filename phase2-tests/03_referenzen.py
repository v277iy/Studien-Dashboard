class Pruefungsleistung:
    def __init__(self, form):
        self.form = form


class Modul:
    def __init__(self, code, pruefungsform):
        self.code = code
        self.pruefung = Pruefungsleistung(pruefungsform)


class Semester:
    def __init__(self, nummer):
        self.nummer = nummer
        self.module = []

    def verschiebe_modul(self, modul, ziel):
        self.module.remove(modul)
        ziel.module.append(modul)


class Studiengang:
    def __init__(self):
        self.semester = []


def main():
    studium = Studiengang()
    erstes = Semester(1)
    zweites = Semester(2)
    studium.semester = [erstes, zweites]

    modul = Modul("OOP-PY", "Portfolio")
    erstes.module.append(modul)
    pruefung = modul.pruefung
    assert studium.semester[0].module[0] is modul
    assert modul.pruefung.form == "Portfolio"

    erstes.verschiebe_modul(modul, zweites)
    assert erstes.module == []
    assert zweites.module[0] is modul
    assert modul.pruefung is pruefung
    print("T3: Objektbeziehungen und Verschieben eines Moduls in ein anderes Semester.")


if __name__ == "__main__":
    main()
