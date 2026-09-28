# Testprogramme zu Phase 2

Die fünf Programme zeigen Grundlagen der objektorientierten Programmierung, JSON-Speicherung und Qt-Oberflächen anhand kleiner, unabhängiger Beispiele.

| Test | Datei | Inhalt |
| --- | --- | --- |
| T1 | `01_datenklassen.py` | Datenklasse mit Konstruktor, Vergleich und eigener Methode; keine automatische Typprüfung. |
| T2 | `02_vererbung.py` | Abstrakte Basisklasse, geerbte Methode und unterschiedliche Fortschrittsberechnung in zwei Unterklassen. |
| T3 | `03_referenzen.py` | Studiengang, Semester, Modul und Prüfungsleistung sind über Referenzen verbunden. Ein Modul wird in ein anderes Semester verschoben. |
| T4 | `04_datentypen_json.py` | Datum, Decimal und Enums werden als Texte in einer JSON-Datei gespeichert und beim Laden wieder umgewandelt. |
| T5 | `05_qt_signale.py` | Ein Button löst die Eingabeprüfung aus. Gültige Eingaben ändern das Modul und die Anzeige, ungültige führen zu einem Hinweis. |

## Ausführen

Im Verzeichnis `phase2-tests/` ausführen. Benötigt werden Python 3.14 und für T5 das Paket PySide6 (`python -m pip install PySide6`).

```bash
for datei in *.py; do
    python -B "$datei" || exit
done
```

Unter Windows, in PowerShell:

```powershell
Get-ChildItem *.py | ForEach-Object {
    python -B $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Test fehlgeschlagen" }
}
```

Jedes Programm prüft die Ergebnisse mit `assert` und gibt bei Erfolg eine kurze Meldung aus. T4 verwendet eine temporäre Datei, T5 läuft ohne sichtbares Fenster. Die Beispiele verändern keine gespeicherten Studiendaten.
