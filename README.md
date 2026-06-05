# RangeLog

RangeLog ist eine lokale PWA zum Tracken von Schiesstrainings. Die App nutzt Flask, SQLite, HTML, CSS und JavaScript.

## Start

```bash
cd rangelog
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Danach im Browser öffnen:

```text
http://127.0.0.1:5000
```

## Funktionen

- Dauerhaft gespeicherte Übungen als wiederverwendbare Profile
- Runs/Sessions als einzelne Durchführungen einer Übung
- Statische Übungen mit Schuss-für-Schuss-Erfassung, Total und Prozent
- Dynamische Übungen mit IPSC Minor, IPSC Major, IDPA, Time Plus, Points Only und Custom Scoring
- Übungsliste mit Filtern, Detailansicht, Favoriten und Mini-Stats
- Canvas-Statistiken sauber pro Übung getrennt
- REST API für Übungen und Runs
- PWA Manifest und Service Worker

Die SQLite-Datenbank wird automatisch unter `instance/rangelog.sqlite` erstellt.

## API

- `GET /api/exercises`
- `POST /api/exercises`
- `GET /api/exercises/<id>`
- `PUT /api/exercises/<id>`
- `DELETE /api/exercises/<id>`
- `POST /api/exercises/<id>/sessions`
