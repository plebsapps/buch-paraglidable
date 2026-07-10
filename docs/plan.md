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
  neue Features.

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
| **C2** | Pipeline in CLI-Schritte zerlegen (download/forecast/tile/publish) | offen |
| **C3** | Web-Inventar: PHP-Endpunkte + .htaccess, Charakterisierungstests | teilweise — Inventar ✅ (docs/web_inventory.md, inkl. Fund MySQL-ApiKeys + .data/.elev-Formate); HTTP-Snapshots offen |
| **D1** | Tiler → Python (numpy/Pillow/mercantile), Pixelvergleich, dann C++/Qt entfernen | offen |
| **D2** | PHP → FastAPI, endpunktweise mit Snapshots; Frontend zunächst 1:1 | offen |
| **D3** | cron_tasks → APScheduler | offen |
| **E** | Datei→DB per Expand and Contract (Alembic, Doppel-Schreiben, Leser umstellen, Rückbau) | offen |

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
Deployment gestuft (Staging-Probelauf auf Referenzdaten → manuelle Freigabe →
Produktion); Details werden bei Etappe D/E konkretisiert.
