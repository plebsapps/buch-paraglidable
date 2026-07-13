# TODO — vereinbarte Reihenfolge (2026-07-12)

Ergänzend zum Etappenplan in docs/plan.md (dort stehen Ziel, Entscheidungen
und Abnahmekriterien; hier nur die vereinbarte Arbeitsreihenfolge).

## 1. Etappe D3: Worker-Container mit APScheduler  ✅ 2026-07-12

`scripts/cron_tasks` → APScheduler im eigenen Compose-Service `worker`
(gleiches eingefrorenes Basis-Image wie die Pipeline). Damit entfällt der
manuelle tägliche Forecast-Lauf. Jobs bleiben einzeln als CLI startbar,
Logging in Container-Stdout.

## 2. Sichtbare Eigenständigkeit (Etappe F, Stufe 1)  ✅ 2026-07-12

Umgesetzt als Variante A „Alpenkarte" (Betreiber-Auswahl aus drei
Entwürfen): OpenTopoMap-Basiskarte mit Attribution, Farbwelt
Tannengrün/Bernstein, eigenes Gleitschirm-Signet (Favicons + Logo),
Wortmarke + Projektzeile im Kopf. Startansicht Alpenraum war bereits
Standard. Vorhersage-Farben rot→grün unangetastet.

## 3. Frontend-Neubau FastAPI + Jinja2 (Etappe F, Stufe 2)  ⬅ in Arbeit

Statische index.html → Jinja2-Templates mit eigenem Layout (Navigation
statt Popup-Sammlung), jQuery raus (Vanilla JS), Leaflet bleibt.
API-Naht (`get.php`) bleibt verhaltensgleich — Golden Master und
API-Snapshots bleiben das Sicherheitsnetz.

- ✅ Teil 1a (2026-07-12): 12 Inline-JS-Blöcke → `www/js/app/`-Module
  (reine Extraktion, Reihenfolge unverändert)
- ✅ Teil 1b (2026-07-12): index.html → Jinja2 (`web/templates/` mit
  12 Partials), FastAPI rendert „/"; Beweis: Rendering **byte-identisch**
  zur alten Datei, Snapshot blieb ohne Neuaufnahme EQUIVALENT
- ✅ Teil 1c (2026-07-12): mobile.html/mobileAndroid.html als Templates
  (byte-identisch verifiziert)
- ✅ Teil 2 (2026-07-12): Navigations-Redesign — Seitenleiste (Entwurf A,
  Betreiber-Auswahl aus drei anklickbaren Entwürfen): Burger + gruppierter
  Drawer, Inhalte docken als Panel an; drawer.js ohne jQuery
- offen: gemeinsames base-Layout der drei Templates, jQuery-Ablösung der
  Bestands-Module (main.js & Co.), ggf. Drawer-Muster auch mobil

## 4. Etappe E: Datei → PostgreSQL (Expand and Contract)  ⬅ End-to-End-Abnahme

Umgesetzt 2026-07-13 (Details docs/plan.md): db-Service + Alembic-Schema
Nr. 1–3, Doppel-Schreiben hinter PARAGLIDABLE_DB_URL (GM unverändert,
EQUIVALENT verifiziert), Vergleichsjob Datei↔DB nach jedem Lauf, echte
API-Schlüssel (3 Snapshots bewusst neu eingefroren), Spot-Leser auf DB
mit Datei-Rückfall. End-to-End-Abnahme ✅ 2026-07-13: erster Produktions-Voll-Lauf (Zyklus
2026071306, 31 min) spiegelte 10 Tage × 33 666 Zellen + je 585 Spots,
Vergleichsjob RESULT: EQUIVALENT. Dabei gefundener Scheduler-Bug
(Modulpfad) als eigener Commit repariert.

---
Weiter offen aus Punkt 3: gemeinsames base-Layout, jQuery-Ablösung der
Bestands-Module, ggf. Drawer-Muster auch mobil.
