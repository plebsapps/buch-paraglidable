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

## 3. Frontend-Neubau FastAPI + Jinja2 (Etappe F, Stufe 2)

Statische index.html → Jinja2-Templates mit eigenem Layout (Navigation
statt Popup-Sammlung), jQuery raus (Vanilla JS), Leaflet bleibt.
API-Naht (`get.php`) bleibt verhaltensgleich — Golden Master und
API-Snapshots bleiben das Sicherheitsnetz; Frontend-Snapshots werden
dann bewusst in Rente geschickt. Etappierbar: erst Desktop, dann mobile.

---
Unabhängig davon offen: Etappe E (Datei → PostgreSQL, echte API-Schlüssel);
Reihenfolge zu 2./3. frei.
