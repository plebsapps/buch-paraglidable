# TODO — vereinbarte Reihenfolge (2026-07-12)

Ergänzend zum Etappenplan in docs/plan.md (dort stehen Ziel, Entscheidungen
und Abnahmekriterien; hier nur die vereinbarte Arbeitsreihenfolge).

## 1. Etappe D3: Worker-Container mit APScheduler  ⬅ in Arbeit

`scripts/cron_tasks` → APScheduler im eigenen Compose-Service `worker`
(gleiches eingefrorenes Basis-Image wie die Pipeline). Damit entfällt der
manuelle tägliche Forecast-Lauf. Jobs bleiben einzeln als CLI startbar,
Logging in Container-Stdout.

## 2. Sichtbare Eigenständigkeit (Etappe F, Stufe 1)

Kleine Hebel mit großer Wirkung, ohne Frontend-Neubau:
- anderer Kartenstil (Basemap) — größter Einzelhebel
- eigenes Farbschema + Typografie in paraglidable.css (Vorhersage-Farben
  rot→grün bleiben fachlich unangetastet)
- eigenes Logo/Favicon (aktuell noch das Original-Logo)
- eigene Startansicht (z. B. Alpenraum)
- Kopfzeile mit Projektkontext (Buch-Praxisfall), nicht nur Footer

## 3. Frontend-Neubau FastAPI + Jinja2 (Etappe F, Stufe 2)

Statische index.html → Jinja2-Templates mit eigenem Layout (Navigation
statt Popup-Sammlung), jQuery raus (Vanilla JS), Leaflet bleibt.
API-Naht (`get.php`) bleibt verhaltensgleich — Golden Master und
API-Snapshots bleiben das Sicherheitsnetz; Frontend-Snapshots werden
dann bewusst in Rente geschickt. Etappierbar: erst Desktop, dann mobile.

---
Unabhängig davon offen: Etappe E (Datei → PostgreSQL, echte API-Schlüssel);
Reihenfolge zu 2./3. frei.
