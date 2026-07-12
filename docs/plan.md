# Umbauplan und Projektstand

Etappenplan der verhaltenserhaltenden Modernisierung (Praxisfall Teil II des
Buchs „Softwaremodernisierung mit selbstgehosteter KI"). Dieses Dokument ist
die maschinen- und ortsunabhängige Quelle für Ziel, Entscheidungen und Stand —
es wird bei jedem Etappenabschluss nachgeführt.

## Zielbild

- Komplette Übersetzung nach Python: Tiler (C++/Qt 5) und Webauslieferung
  (Apache/PHP) werden portiert; der ML-Kern ist bereits Python.
- PostgreSQL **nur** für Vorhersageergebnisse, Spots, Läufe/Metadaten;
  große Binärdaten (GRIB-Wetterdateien, Kacheln, Trainingsdaten) bleiben
  bewusst dateibasiert auf Volumes.
- Alles läuft in Docker (Compose); Betrieb als eigene Instanz unter
  **paraglidable.plebsapps.de** (eigener Ubuntu-Server).
- Leitplanke über allem: **das Prognoseverhalten ändert sich nicht**
  (Golden Master entscheidet, nicht die Diskussion).
- Ausdrücklich außer Scope: neues Modell, Neutraining, Prognoseverbesserung,
  neue Features. Bewusste Ausnahme seit 2026-07-11: eine eigenständige
  visuelle Identität des Frontends (Etappe F, nach D2) — das
  Prognoseverhalten bleibt davon unberührt.

## Getroffene Entscheidungen

| Thema | Entscheidung | Begründung |
|---|---|---|
| Repo | Öffentlich, GPLv3, volle Original-Historie, `upstream`-Remote aufs Original | Copyleft + faire Attribution; Diffs gegen kommende „v2" möglich |
| Web-Framework | FastAPI + Uvicorn | Original ist API + statisches Frontend; OpenAPI-Doku = dokumentierte Naht |
| Tiler-Ersatz | numpy + Pillow + mercantile (ggf. scipy) | Werte→Farbkacheln ist Array-Rechnung + PNG; pixelgenau kontrollierbar |
| Scheduler | APScheduler im Worker-Container statt Cron | Logging in Container-Stdout, testbar, Läufe als DB-Zeilen; Jobs bleiben als CLI startbar |
| Datenbank | postgis/postgis-Image, `geom`-Spalten erst bei Bedarf | Umstieg später wäre Migration; PostGIS-Konzepte erst, wenn sie Nutzen bringen |
| Migrationen | Alembic ab Schema Nr. 1 | Versionierte, reversible Migrationen von Anfang an |
| GM-Datenhaltung | Release `golden-master-v1` (Eingabe-GRIBs, Referenzlauf, Trainingsdaten, Elevation) | Zu groß für Git, unveränderlich per Definition, CI lädt per `gh release download` |
| Frontend-Identität | Sichtbarer Derivat-Hinweis sofort (Footer, 2026-07-11); vollständiges Redesign erst als Etappe F **nach** D2 | HTTP-Snapshots bleiben bis zur D2-Portierung das Sicherheitsnetz; Redesign vor/während D2 würde es zerstören. Hinweis dient GPLv3-Attribution und Abgrenzung zu paraglidable.com |

## Ziel-Architektur (Docker Compose, Endzustand)

| Service | Basis | Aufgabe |
|---|---|---|
| `postgres` | postgis/postgis (Digest-gepinnt) | Läufe, Spots, Ergebnisse, Metadaten |
| `web` | Python 3.11+, FastAPI + Uvicorn | API + statisches Frontend + Kachel-Auslieferung |
| `worker` | gleiches Basis-Image | Pipeline GFS-Download → Forecast → Tiler; APScheduler |

Named Volumes: `grib-data`, `tiles`, `training-data`, `golden-master`,
`pg-data`. Ein Dockerfile, zwei Targets; jeder Job auch manuell als CLI.
Reverse Proxy/TLS für paraglidable.plebsapps.de ist Teil von Etappe-
übergreifendem Deployment (Kapitel 20 des Buchs), nicht der Compose-Basis.

### PostgreSQL-Schema (Skizze für Etappe E)

```
forecast_runs   id, gfs_cycle, model_version, code_git_sha, status,
                started_at, finished_at, params jsonb, error
spots           id, name, lat, lon, country, meta jsonb, source
spot_forecasts  (run_id, spot_id, valid_date) PK, flyability, crossability, attributes jsonb
cell_forecasts  (run_id, cell_id, valid_date) PK, values      -- Tiler-Input
tile_sets       id, run_id, layer, valid_date, zoom_min/max, base_path
```

## Etappen und Stand

Pflichtjob ab sofort: `compare_golden_master` grün vor jedem Merge/Push.

| Etappe | Inhalt | Stand |
|---|---|---|
| **A1** | Original-Image baut wieder (archäologisches Pinning) | ✅ 2026-07-10 — 3 Reparaturen: mathjax-node-cli deaktiviert (npm 3.x/Registry), glob3 entfernt (von PyPI gelöscht), Basemap auf v1.2.1rel gepinnt |
| **A2** | Daten geladen, GFS-Zyklus archiviert | ✅ 2026-07-10 — Google-Drive-Downloader repariert (stiller Fehlschlag bei großen Dateien), make/g++ ergänzt; Zyklus 2026-07-09 06z (3 GRIBs) gesichert |
| **A3** | Golden Master eingefroren | ✅ 2026-07-10 — 3 Läufe **byte-identisch**; Runner + dreistufiger Vergleich im Repo; Referenz im Release |
| **B** | Pinnen + CI | ✅ 2026-07-10 — Pinnung (Digest + Lockfile, GM-verifiziert); CI grün: Golden-Master-Vergleich als Pflichtjob bei jedem Push/PR. Lehrstück: erster CI-Lauf deckte 1-ULP-Drift auf fremder Hardware auf → Toleranzen begründet kalibriert (atol=2e-6 = Textformat-Auflösung; .data-Byte-Kipper ≤0,5 % toleriert) |
| **C1** | Format-Naht forecast→tiler | ✅ 2026-07-10 — docs/predictions_format.md + pipeline/predictions_io.py, Round-Trip byte-identisch |
| **C2** | Pipeline in CLI-Schritte zerlegen (download/forecast/tile/publish) | ✅ 2026-07-11 — `Forecast.main()` in vier Schrittmethoden zerlegt (reine Extraktion, Dateien als Naht); CLI `python -m pipeline run\|download\|forecast\|tile\|publish` mit Pfad-Overrides. Doppelt verifiziert: GM über Legacy-Runner EQUIVALENT **und** schrittweiser CLI-Lauf auf GM-Eingabe EQUIVALENT; 7/7 Unit-Tests. Stolperstein: Python 3.6 im eingefrorenen Container (argparse-Subparser) |
| **C3** | Web-Inventar: PHP-Endpunkte + .htaccess, Charakterisierungstests | ✅ 2026-07-10 — Inventar (docs/web_inventory.md, Funde: MySQL-ApiKeys, .data/.elev-Formate, fehlende mail_helper.php) + 13 HTTP-Snapshots (golden_master/snapshot_www.py, zweifach verifiziert) |
| **S** | Server-Inbetriebnahme paraglidable.plebsapps.de (vor C2): Setup nach CLAUDE.md, GM-Verifikation auf Server-Hardware, Reverse Proxy + TLS + Basic-Auth, manueller Forecast-Lauf | ✅ 2026-07-11 — GM auf Server-Hardware EQUIVALENT (dritte Hardware, Toleranzen unverändert), 13/13 Snapshots, 3/3 Tests; live hinter nginx+TLS+Basic-Auth auf Port 8006 (8001 belegt); Forecast-Lauf 2026-07-11 06z. Befund: nur 1,8 GB RAM → Swap auf 9 GiB erweitert (docs/deployment.md) |
| **D1** | Tiler → Python (numpy/Pillow/mercantile), Pixelvergleich, dann C++/Qt entfernen | ✅ 2026-07-11 — `pipeline/tiler.py` (numpy+Pillow, ohne mercantile: eigene 40-Zeilen-Portierung von tilesmath); Pixelvergleich **aller** Kacheln: 2521/2703 PNGs exakt, 182 mit ±1 (226 von 177 Mio. Pixeln, 1-ULP-sin), 269/269 .data byte-identisch (compare_tiler_outputs.py); GM-Lauf mit Python-Tiler EQUIVALENT; C++/Qt entfernt, Corner-Cache als eingefrorenes Release-Artefakt (gm_corner_cache.tar.gz), Python-Fallback byte-identisch verifiziert |
| **D2** | PHP → FastAPI, endpunktweise mit Snapshots; Frontend zunächst 1:1 | ✅ 2026-07-11 — `web/app.py` (FastAPI) + `web/php_compat.py` (PHP-7.2-Semantik nachgebildet, unit-getestet); Portierungsentscheidungen in docs/web_inventory.md; **13/13 Snapshots EQUIVALENT** gegen Port und weiterhin gegen Original; web-Service in docker-compose.yml (python:3.11-slim digest-gepinnt, Port 8007). Produktivschaltung nginx 8006→8007 am 2026-07-12 erfolgt und verifiziert (docs/deployment.md); Betreiber-Entscheidung: keine Beobachtungsphase, FastAPI ab sofort einziger Webpfad. Legacy-Container läuft nur noch als Pipeline-Laufzeitumgebung weiter (bis D3) |
| **D3** | cron_tasks → APScheduler | offen |
| **E** | Datei→DB per Expand and Contract (Alembic, Doppel-Schreiben, Leser umstellen, Rückbau) | offen |
| **F** | Eigenständige Identität (nach D2): eigenes Design/Name-Auftritt, og-Meta/Titel bereinigen, Kontakt-/Spenden-Links des Originals ersetzen, mobile-Seite einbeziehen; Snapshots danach bewusst neu einfrieren | **Teil 1 ✅ 2026-07-12** — Identitäts-/Link-Bereinigung: Autor-Links (Donate/Social/Kontakt/App/V2) und Google-Analytics-Tracking entfernt, GitHub/Kontakt → plebsapps-Repo bzw. ralfwbalz.ch, og-Meta + API-Beispiele → paraglidable.plebsapps.de, Betreiber-Zeile im Footer; 2 Snapshots bewusst neu eingefroren (index_html, gtag→404), 13/13 EQUIVALENT. Name „Paraglidable" bleibt (Betreiber-Entscheidung); Oberfläche vollständig auf Deutsch übersetzt inkl. About-Text mit Dank an den Original-Autor (2026-07-12); visuelles Redesign optional offen |

## Risiken / Merkposten

- NOMADS: alte CGI-URLs funktionieren noch (Stand 2026-07-10), Migration auf
  neue NOMADS-URLs oder AWS-Open-Data-Mirror einplanen; Rate-Limits beachten.
- Upstream „v2" in Arbeit: `git log upstream/master` gelegentlich sichten;
  Antoine Meler informieren (Fairness) — Entscheidung liegt beim Autor.
- Trainingsdaten (Google Drive, 200 MB): Lizenz ungeklärt, im Release
  gespiegelt, nicht wiederholt von Paraglidable-Quellen ziehen.
- Reproduzierbarkeit des Trainings besteht nicht (bekannt, akzeptiert):
  Gewichte als unersetzliches Artefakt sichern.
- Windows-Entwicklung: LF erzwungen; `core.autocrlf` steht systemweit auf
  true — frische Clones auf Windows brauchen `git config core.autocrlf false`
  vor dem Checkout oder einen Re-Checkout (siehe CLAUDE.md).

## Betrieb (Ausblick, Kapitel 20)

Zielumgebung: eigener Ubuntu-Server, Instanz unter paraglidable.plebsapps.de.
Zwischenphase ab Etappe S: Legacy-Webschicht (Apache/PHP im eingefrorenen
Container) läuft hinter dem vorhandenen Reverse Proxy mit TLS und
**Basic-Auth**, bis die FastAPI-Webschicht (D2) sie ablöst; Forecast-Läufe
bis D3 manuell, kein Cron. Serverbefund und Proxy-Integration: docs/deployment.md.
Deployment gestuft (Staging-Probelauf auf Referenzdaten → manuelle Freigabe →
Produktion); Details werden bei Etappe D/E konkretisiert.
