# Umbauplan und Projektstand

Etappenplan der verhaltenserhaltenden Modernisierung (Praxisfall Teil II des
Buchs „Softwaremodernisierung mit KI"). Dieses Dokument ist
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
übergreifendem Deployment (Kapitel 14 des Buchs), nicht der Compose-Basis.

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
| **D3** | cron_tasks → APScheduler | ✅ 2026-07-12 — `pipeline/scheduler.py` im Compose-Service `worker` (eingefrorenes Pipeline-Image + apscheduler==3.9.1, letzte Py-3.6-Linie): forecast */30min als Subprozess (Speicher wird je Lauf frei; Voll-Lauf nur bei neuem GFS-Zyklus, max_instances=1), commit.txt */21min (reine Python-HEAD-Auflösung), clean 02:00. Jobs einzeln als CLI startbar. Nicht portiert (begründet im Modulkopf): check_server.py, reboot.sh, renew_certificates.sh. Verifiziert: Erst-Trigger 12:30 startete korrekt den neuen 06z-Zyklus |
| **E** | Datei→DB per Expand and Contract (Alembic, Doppel-Schreiben, Leser umstellen, Rückbau) | **Umgesetzt 2026-07-13, End-to-End-Abnahme läuft** — E1: postgis-Service (digest-gepinnt, ohne Host-Port, eng konfiguriert für 1,8 GB RAM; Zugangsdaten via .env) + Alembic-Schema Nr. 1–3. E2 (Expand): step_publish spiegelt je Tag Läufe/Zellen/Spots/Kachel-Metadaten hinter dem Env-Seam `PARAGLIDABLE_DB_URL` (nur worker; GM-Läufe und Legacy-Container unverändert — GM nach dem Seam-Einbau EQUIVALENT); Aufbewahrung 8 Läufe (clean-Job, CASCADE). E3 (Vergleichsjob): verify_db_mirror re-serialisiert Zellen im exakten Dateiformat gegen den beim Spiegeln festgehaltenen SHA-256 der Quelldatei, Spots feldgenau gegen spots.json; läuft nach jedem Worker-Lauf, Negativprobe verifiziert. E4: echte API-Schlüssel (Ersatz des toten MySQL-Teils; bewusste Abweichung: Schlüssel im Antwort-Body statt Mail — dokumentiert, 3 Snapshots neu eingefroren, 13/13 EQUIVALENT). E5 (Migrate): get.php-Spot-Zweig liest aus der DB, Datei-Rückfall = Rückweg. **Contract bewusst begrenzt:** predictions.txt/spots.json bleiben die GM- bzw. Frontend-Schnittstelle (Frontend lädt spots.json statisch, GM-Referenz ist dateibasiert); zurückgebaut ist der tote MySQL-Pfad (500-Stubs) |
| **F** | Eigenständige Identität (nach D2): eigenes Design/Name-Auftritt, og-Meta/Titel bereinigen, Kontakt-/Spenden-Links des Originals ersetzen, mobile-Seite einbeziehen; Snapshots danach bewusst neu einfrieren | **Teil 1 ✅ 2026-07-12** — Identitäts-/Link-Bereinigung: Autor-Links (Donate/Social/Kontakt/App/V2) und Google-Analytics-Tracking entfernt, GitHub/Kontakt → plebsapps-Repo bzw. ralfwbalz.ch, og-Meta + API-Beispiele → paraglidable.plebsapps.de, Betreiber-Zeile im Footer; 2 Snapshots bewusst neu eingefroren (index_html, gtag→404), 13/13 EQUIVALENT. Name „Paraglidable" bleibt (Betreiber-Entscheidung); Oberfläche vollständig auf Deutsch übersetzt inkl. About-Text mit Dank an den Original-Autor (2026-07-12). **Stufe 2 (visuelle Eigenständigkeit) ✅ 2026-07-12**: Variante „Alpenkarte" — OpenTopoMap-Basiskarte (Attribution im Footer/mobil), Farbwelt Tannengrün/Bernstein, eigenes Gleitschirm-Signet (Favicons/Logo), Wortmarke+Projektzeile im Kopf; Küstenlinien in Produktions-Kacheln abgeschaltet (env-Schalter, GM-Pfad unverändert). Offen bleibt nur der optionale Frontend-Neubau (Jinja2, TODO.md Punkt 3) |
| **G** | Abhängigkeiten gestuft aktualisieren (im Buch „Etappe B"; im Plan bis 2026-07-14 nicht vorgesehen — die Lücke fiel erst beim Abgleich der Buch-Aussagen gegen dieses Repository auf. Stufe **B** oben ist *Pinnen + CI*, also etwas anderes) | ✅ 2026-07-14 — **verspätet und außer der Reihe** (nach D, E, F und der Produktivschaltung); die Zuordnungsschärfe „jede GM-Abweichung stammt aus der Umgebung" war damit verloren — der Vergleich blieb grün, aber das war Glück. Erstinventur (OSV + pip-audit): **961 bekannte Befunde in 26 von 115 Paketen** der Pipeline, 8 im Webbaum; allein TensorFlow 2.1.0 trägt 743. Fünf Schritte, je eigener Commit und eigener Nachweis: **B1** fastapi 0.115.6→0.139.0 (zieht starlette 0.41.3→**1.3.1**, 8 CVEs→0; API-Bruch mechanisch angepasst — starlette 1.x hat den env_options-Durchgriff von Jinja2Templates entfernt, `autoescape=True` bewusst festgeschrieben, sonst stille Rendering-Änderung); **B2** uvicorn→0.51.0; **B3** SQLAlchemy 2.0.51 + alembic 1.18.5 (untrennbar; zusätzlich Migrationskette bis 0003 (head) geprüft); **B4** psycopg2-binary→2.9.12 — B1–B4 je **13/13 Snapshots EQUIVALENT**; **B5** requests 2.27.1 + urllib3 1.26.20 + certifi 2025.4.26 (untrennbar, requests 2.22.0 deckelt urllib3<1.26): certifi **5→0** (Vertrauensspeicher war 6 J. 7 Mon. alt), urllib3 22→10, requests 8→8 = **kein Gewinn** (Fixes verlangen Py3.7) — angehoben als Türöffner, heilt nebenbei den seit Etappe A inkonsistenten Baum (idna 3.10 trotz requests-Bedingung idna<2.9; `pip check` jetzt sauber). Nachweis B5 zweiteilig, weil der GM auf eingefrorener Eingabe läuft und den Downloader nie anfasst: **GM EQUIVALENT** (Toleranzen unverändert, Netz vorher auf dem Ausgangsstand ebenfalls geprüft) **+ echter TLS-Abruf gegen NOMADS (200)**. Ausgerollt am 2026-07-14 auf alle vier Container (Worker vor Web; Legacy-Container mitgezogen, weil er die GM-Laufzeit ist), Nachweise und Rückweg (`rollback-vor-b`-Tags) in docs/deployment.md. **Restliste: docs/abhaengigkeiten.md** — 944 der 961 Befunde hängen an einer Wurzel, dem Basisimage (Python 3.6 EOL 2021, Ubuntu 18.04 EOL 2023) = Laufzeit des eingefrorenen Modells; dessen Wechsel ist keine Abhängigkeitsfrage, sondern eine fachliche Entscheidung über das Prognoseverhalten (VK01). Nebenbefund: ~70 Befunde stammen aus einem Jupyter-Stack, den kein Produktivcode nutzt — dort ist Entfernen richtig, nicht Aktualisieren (eigener Auftrag) |

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

## Betrieb (Ausblick, Kapitel 14)

Zielumgebung: eigener Ubuntu-Server, Instanz unter paraglidable.plebsapps.de.
Zwischenphase ab Etappe S: Legacy-Webschicht (Apache/PHP im eingefrorenen
Container) läuft hinter dem vorhandenen Reverse Proxy mit TLS und
**Basic-Auth**, bis die FastAPI-Webschicht (D2) sie ablöst; Forecast-Läufe
bis D3 manuell, kein Cron. Serverbefund und Proxy-Integration: docs/deployment.md.
Deployment gestuft (Staging-Probelauf auf Referenzdaten → manuelle Freigabe →
Produktion); Details werden bei Etappe D/E konkretisiert.
