# Deployment: paraglidable.plebsapps.de (Etappe S)

Serverbefund und Inbetriebnahme-Protokoll gemäß `docs/server_briefing.md`.
Stand: 2026-07-11.

## Serverbefund (Bestandsaufnahme 2026-07-11)

| Prüfung | Befund |
|---|---|
| Architektur | x86_64 ✅ |
| RAM | **1,8 GB gesamt, ~0,8 GB verfügbar; Swap 2 GB (573 MB belegt)** — deutlich unter dem Richtwert ≥ 8 GB 🛑 |
| Platte | 77 GB gesamt, 63 GB frei ✅ (Richtwert ≥ 15 GB) |
| Docker | 29.1.3, Compose v2.40.3 ✅ |
| Reverse Proxy | nginx (systemd-Dienst) mit certbot; je Subdomain eine vhost-Datei in `/etc/nginx/sites-enabled/`, `proxy_pass` auf localhost-Port, Let's-Encrypt-Zertifikate „managed by Certbot" |
| DNS | `dig +short paraglidable.plebsapps.de` → 217.154.144.59 = Server-IP ✅ |
| gh | eingeloggt (Account plebsapps); Release `golden-master-v1` mit `gm_reference.tar.gz` und `gm_data.tar.gz` erreichbar ✅ |
| Belegte Ports | 127.0.0.1:8000–8005 (pdb, ralfwbalz, yoga, offerte, bewerbung, schule) sowie 3 Postgres-Container ohne Host-Port |

## Betreiber-Entscheidungen

1. **RAM-STOPP-Kriterium** (Briefing Schritt 1): Der Betreiber hat entschieden,
   den Swap um ein 8-GB-Swapfile zu erweitern und den Golden-Master-Lauf zu
   versuchen. Der Ausgang wird ehrlich dokumentiert — auch ein Misserfolg
   (OOM, unvertretbare Laufzeit) ist Befund, kein Anlass zum Tricksen.
2. **Container-Port**: Abweichend vom Briefing (127.0.0.1:8001) läuft der
   Paraglidable-Container auf **127.0.0.1:8006**, weil 8001 bereits durch den
   ralfwbalz-Container belegt ist.

## Inbetriebnahme-Protokoll

### Setup (2026-07-11)

- Release `golden-master-v1` heruntergeladen (`gm_reference.tar.gz` 307 MB,
  `gm_data.tar.gz` 222 MB), entpackt: `golden_master/input` (158 MB),
  `golden_master/reference` (238 MB), `neural_network/bin/data` (490 MB),
  `tiler/_cache/elevation` (50 MB).
- `docker build -t paraglidable ./docker/` erfolgreich (Image 5,78 GB).
- Container gestartet mit `-p 127.0.0.1:8006:80` (Abweichung: Port 8006,
  localhost-Bindung — Proxy terminiert TLS).
- `build_tiler.sh` erfolgreich, Binary `tiler/Tiler/Tiler` (159 KB).

### Webschicht (2026-07-11)

- Apache via `scripts/start_server.sh` gestartet; `curl http://127.0.0.1:8006/`
  liefert die Startseite (HTTP 200).
- `www/data` befüllt (Voraussetzung der Snapshots, siehe Kopf von
  `golden_master/snapshot_www.py`): GM-Tag-Tiles als **Kopie** aus
  `golden_master/reference/tiles/2026-07-09` (bewusst kein Symlink, damit
  die Webschicht nie in die eingefrorene Referenz schreiben kann);
  `www/data/elevation` als Symlink auf `tiler/_cache/elevation`
  (dokumentierter Weg aus `scripts/download_elevation_tiles.py`).
- HTTP-Snapshots: `python3 golden_master/snapshot_www.py check` im Container →
  **13/13 OK, RESULT: EQUIVALENT**.

### Golden Master auf dieser Hardware (2026-07-11)

Lauf mit `PYTHONHASHSEED=0` nach erweitertem Swap (Gesamt 9 GiB), Vergleich
gegen `golden_master/reference` mit den kalibrierten Standard-Toleranzen:

```
[OK   ] predictions.txt within tolerance (max relative deviation: 1.300e-04)
[OK   ] tiles: 51 of 2703 sampled and compared
[OK   ] data tiles: 269 compared (81 quantization-boundary byte flips tolerated)
[OK   ] spots.json equivalent
RESULT: EQUIVALENT
```

Dritte verifizierte Hardware (nach Entwicklungsrechner und GitHub-CI);
Toleranzen unverändert.

### Unit-Tests (2026-07-11)

```
Ran 3 tests in 0.665s
OK
```
(`python -m unittest discover -s pipeline/tests` im Container: 3/3 grün.)

### Manueller Forecast-Lauf (2026-07-11)

- Ausgeführt wie `scripts/cron_tasks/update_forecasts.sh`, aber von Hand
  (`docker exec -w /workspaces/Paraglidable/neural_network paraglidable
  python3 forecast.py`) — **kein Cron eingerichtet** (kommt mit D3).
- Verwendeter GFS-Zyklus: **2026-07-11 06z** (aktuell, NOMADS erreichbar;
  der Rückfall auf den archivierten GM-Zyklus war nicht nötig).
- Ergebnis: `www/data/tiles/2026-07-10` … `2026-07-20` vollständig
  (256er-Kacheln, spots.json, progress.txt = 100). Die API liefert für den
  aktuellen Tag echte Werte, z. B.
  `get.php?tx=65&ty=45&x=128&y=128&zoom=7&date=2026-07-11` →
  `0.502,0.0392,0.7373,0.3961,0,0.3255`.
- Log-Hinweis: eine Warnung „Meteo files not found" für den nur teilweise
  verfügbaren Vortages-Zyklus 2026-07-10 06z; der Lauf ist danach regulär
  mit dem 06z-Zyklus vom 2026-07-11 durchgelaufen.

### Proxy-Integration (2026-07-11)

- vhost: `/etc/nginx/sites-available/paraglidable.plebsapps.de`
  (Symlink in `sites-enabled/`), nach dem Muster der bestehenden
  plebsapps.de-Subdomains: `proxy_pass http://127.0.0.1:8006`, gleiche
  proxy_set_header-Zeilen, Port-80-Block leitet per 301 auf HTTPS um.
- TLS: Let's Encrypt via `certbot --nginx`, Zertifikat
  `/etc/letsencrypt/live/paraglidable.plebsapps.de/` (gültig bis 2026-10-09,
  automatische Erneuerung durch den certbot-Timer).
- Basic-Auth: `auth_basic` mit `/etc/nginx/.htpasswd_paraglidable`
  (ein Benutzer `paraglidable`; Zugangsdaten dem Betreiber übergeben,
  nicht im Repo). Schützt die Legacy-Webschicht (PHP 7.2/Ubuntu 18.04 im
  eingefrorenen Container) bis zur Portierung (D2).
- Stolperstein, dokumentiert: Beim ersten Versuch war der vhost wegen eines
  im Terminal umgebrochenen Befehls noch nicht installiert; `certbot --nginx`
  hängte die paraglidable-Blöcke deshalb an `sites-available/default` an
  (Antwort: 444). Korrigiert: Blöcke aus `default` entfernt (Backup
  `default.bak-paraglidable-*`), richtige vhost-Datei installiert.
- Verifikation: `https://paraglidable.plebsapps.de/` → **401** ohne, **200**
  mit Credentials; `http://…` → **301** auf HTTPS.

## Startbefehle (Referenz)

Der Container läuft seit 2026-07-11 mit `--restart unless-stopped` und
`scripts/container_start.sh` als Startbefehl (Apache im Vordergrund als
PID 1). Nach Container- oder Server-Neustart kommt die Webschicht damit
ohne manuellen Eingriff wieder hoch; `start_server.sh` wird nur noch für
manuelle Sonderfälle gebraucht.

```bash
# Container neu anlegen (nur nach docker rm nötig)
docker run -d --name paraglidable --restart unless-stopped \
  -p 127.0.0.1:8006:80 \
  -v /home/ralf/buch-paraglidable:/workspaces/Paraglidable \
  paraglidable sh /workspaces/Paraglidable/scripts/container_start.sh

# Forecast-Läufe: seit D3 automatisch durch den Worker (siehe unten).
# Manueller Einzellauf bei Bedarf weiterhin möglich:
docker exec -w /workspaces/Paraglidable paraglidable python -m pipeline run

# FastAPI-Webschicht (D2), Port 127.0.0.1:8007
docker compose up -d --build web
# Verifikation (13 Charakterisierungstests; localhost, nicht 127.0.0.1!):
SNAPSHOT_BASE=http://localhost:8007 python3 golden_master/snapshot_www.py check

# Worker (D3): APScheduler ersetzt cron — kein manueller Tageslauf mehr
docker compose up -d --build worker
docker logs -f paraglidable-worker           # Job-Log (stdout)
docker exec paraglidable-worker python3 pipeline/scheduler.py clean  # Einzeljob
```

### Worker-Betrieb (seit D3, 2026-07-12)

Der Service `paraglidable-worker` (eingefrorenes Pipeline-Image +
APScheduler) pollt alle 30 min; ein Voll-Lauf passiert nur, wenn auf
NOMADS ein neuer GFS-Zyklus liegt (max. 4×/Tag, je ~1¾ h auf dieser
Hardware; parallele Trigger werden per max_instances=1 übersprungen).
Bei Erstinbetriebnahme wurde der Zyklus-Zustand (`/tmp/lastForecastTime`)
aus dem Legacy-Container übernommen, um einen Doppellauf zu vermeiden —
nach einem Container-Neubau läuft schlimmstenfalls ein Zyklus doppelt.
Merkposten: 4 Voll-Läufe/Tag sind deutlich mehr Last als das bisherige
manuelle Regime (1/Tag); wenn der Server leidet, Kadenz im Scheduler
drosseln (eigener, begründeter Commit).

Seit Etappe F setzt der Worker `PARAGLIDABLE_DRAW_BORDERS=0`: die
Produktions-Kacheln werden ohne eingebrannte Küstenlinien gerendert
(OpenTopoMap bringt eigene Küsten mit). Golden-Master-Läufe laufen ohne
die Variable — dort bleibt das Referenzverhalten (mit Linien) erhalten.
Wirkung ab dem nächsten Voll-Lauf nach Container-Neuanlage.

## Produktivschaltung der FastAPI-Webschicht (D2 → live)

**Erfolgt am 2026-07-12** (Betreiber): vhost von 8006 auf 8007 umgestellt,
`nginx -t` + Reload. Verifikation über nginx: 401 ohne / 200 mit Credentials,
HTTP→HTTPS-301; ein voller Seitenaufruf im Browser landete nachweislich im
uvicorn-Log (Startseite, Assets, 226 Kachel-Anfragen, `get.php` mit echten
Werten für den Tag). Abweichungen im Log sind die erwarteten eingefrorenen
Verhalten: 404 für den 11. Tag hinter dem letzten Lauf, 500 für
`get.php?key=…` (mysqli-Zustand, bis Etappe E). Der Befehl (Referenz):

```bash
# im vhost paraglidable.plebsapps.de proxy_pass von 8006 auf 8007 stellen
sudo sed -i 's/127\.0\.0\.1:8006/127.0.0.1:8007/' /etc/nginx/sites-available/paraglidable.plebsapps.de
sudo nginx -t && sudo systemctl reload nginx
```

Rückweg (Rollback): dieselbe Zeile zurück auf 8006. Betreiber-Entscheidung
2026-07-12: Auf die geplante Beobachtungsphase („einige Forecast-Zyklen")
wird verzichtet — die Instanz ist nicht produktionskritisch, FastAPI ist ab
sofort der einzige Webpfad. Der Legacy-Container bleibt trotzdem laufen:
nicht mehr als Webschicht, sondern als eingefrorene Laufzeitumgebung der
Forecast-Pipeline (Python 3.6/TF); er entfällt erst mit Etappe D3.

Stolperstein, dokumentiert: Der erste Umschaltversuch lief mit einem
Tippfehler im vhost-Dateinamen ins Leere (`sed` bricht ab, bevor nginx
angefasst wird) — folgenlos, aber ein Argument dafür, nach jedem
sudo-Handgriff den Ist-Zustand zu prüfen (`grep proxy_pass …`) statt dem
Kommando-Exit zu vertrauen.

## Auslieferung Etappe B (2026-07-14)

Aktualisierte Abhängigkeiten ausgerollt (Freigabe: Betreiber). Alle vier
Container auf neuen Ständen, Reihenfolge Worker vor Webschicht:

```bash
docker tag paraglidable:b5-test paraglidable   # GM-verifiziertes Image
docker compose up -d --build worker
docker compose up -d --build web
docker rm -f paraglidable && docker run -d --name paraglidable \
  --restart unless-stopped -p 127.0.0.1:8006:80 \
  -v /home/ralf/buch-paraglidable:/workspaces/Paraglidable \
  paraglidable sh /workspaces/Paraglidable/scripts/container_start.sh
```

Der Legacy-Container wird bewusst mitgezogen: Er ist die Laufzeit der
Golden-Master-Läufe; liefe er auf alten Ständen, prüfte das Netz etwas
anderes als das, was produktiv rechnet.

Nachweise nach dem Ausrollen: Startseite 200, Referenzkachel 200,
Datenendpunkt mit echten Werten, ausgelieferter Commit 5481634d, nginx
401 ohne Zugangsdaten. 13/13 Schnittstellenaufzeichnungen gegen die
laufende Instanz EQUIVALENT. TLS-Abruf des Downloaders gegen NOAA aus
dem ausgerollten Worker: 200 mit certifi 2025.04.26.

**Rückweg:** Die vorherigen Images liegen als Tags `rollback-vor-b`
(`paraglidable`, `buch-paraglidable-web`, `buch-paraglidable-worker`).
Rollback = Tag zurücksetzen und Container neu anlegen; keine Daten und
keine Formate betroffen, deshalb trägt der Rückweg ohne Sonderschritte.

## Auslieferung Etappe G, Entrümpelung (2026-07-15)

Jupyter-Stack aus dem Produktionsimage entfernt und ausgerollt (Freigabe:
Betreiber). Die Webschicht war nicht betroffen (eigenes Image auf
python:3.11-slim), deshalb nur Pipeline-Image, Worker und
Legacy-Container:

```bash
docker tag paraglidable:nojup paraglidable   # GM-verifiziertes Image
docker compose up -d --build worker
docker rm -f paraglidable && docker run -d --name paraglidable \
  --restart unless-stopped -p 127.0.0.1:8006:80 \
  -v /home/ralf/buch-paraglidable:/workspaces/Paraglidable \
  paraglidable sh /workspaces/Paraglidable/scripts/container_start.sh
```

Stand nach dem Ausrollen: Legacy-Container 63 Pakete, Worker 66
(+ apscheduler, tzlocal, psycopg2-binary), **null Jupyter-Pakete**.

Nachweise: Startseite 200, Referenzkachel 200, Datenendpunkt mit echten
Werten, nginx 401 ohne Zugangsdaten; 13/13 Schnittstellenaufzeichnungen
gegen die laufende Instanz EQUIVALENT; Unit-Tests 17/17 im ausgerollten
Legacy-Container; TLS-Abruf gegen NOAA aus dem ausgerollten Worker 200.
Golden Master war vor dem Ausrollen mit diesem Image EQUIVALENT
(unveränderte Toleranzen).

**Rückweg:** Tags `rollback-vor-g` (`paraglidable`,
`buch-paraglidable-worker`) = Stand nach Etappe B, mit Jupyter. Der
ältere Stand vor Etappe B liegt weiterhin unter `rollback-vor-b`.

## Auslieferung Etappe G, basemap (2026-07-15)

basemap samt pyshp aus dem Produktionsimage entfernt und ausgerollt
(Freigabe: Betreiber). Wie bei der Jupyter-Entrümpelung nur
Pipeline-Image, Worker und Legacy-Container — die Webschicht hat ihr
eigenes Image:

```bash
docker tag paraglidable:latest paraglidable:rollback-vor-basemap
docker tag buch-paraglidable-worker:latest buch-paraglidable-worker:rollback-vor-basemap
docker tag paraglidable:nobm paraglidable   # GM-verifiziertes Image
docker compose up -d --build worker
docker rm -f paraglidable && docker run -d --name paraglidable \
  --restart unless-stopped -p 127.0.0.1:8006:80 \
  -v /home/ralf/buch-paraglidable:/workspaces/Paraglidable \
  paraglidable sh /workspaces/Paraglidable/scripts/container_start.sh
```

Stand nach dem Ausrollen: Legacy-Container 61 Pakete (vorher 63), Worker
64 (+ apscheduler, tzlocal, psycopg2-binary), Image 5,56 → **4,96 GB**.
basemap und pyshp weg, `pyproj` und `pygrib` unverändert vorhanden —
pyproj sieht wie ein basemap-Anhängsel aus, wird aber von pygrib
gebraucht (siehe docs/abhaengigkeiten.md).

Nachweise: Kern-Importe im ausgerollten Container OK (TF 2.1.0, numpy
1.18.1, pygrib, pyproj, Pillow), forecast.py/trained_model/grib_reader
und pipeline.tiler/predictions_io importierbar; Startseite 200,
Kachel 200, `vignette.png` 200, Datenendpunkt mit echten Werten,
ausgelieferter Commit 51358262, nginx 401 ohne Zugangsdaten; 13/13
Schnittstellenaufzeichnungen gegen die laufende Instanz EQUIVALENT;
Unit-Tests 17/17 im ausgerollten Legacy-Container; `pip check` ohne
Befund; TLS-Abruf gegen NOAA aus dem ausgerollten Worker 200 (certifi
2025.04.26); Scheduler nimmt die Jobs auf. Golden Master war vor dem
Ausrollen mit diesem Image EQUIVALENT (unveränderte Toleranzen).

Keine Sicherheitsbefunde gewonnen — basemap hatte null; der Schritt ist
reine Entrümpelung. Tagesbilanz Etappe B + G am Produktionsimage: 128 →
61 Pakete, 5,78 → 4,96 GB, 996 → 888 Befunde.

**Rückweg:** Tags `rollback-vor-basemap` (`paraglidable`,
`buch-paraglidable-worker`) = Stand nach der Jupyter-Entrümpelung, mit
basemap. Ältere Stände: `rollback-vor-g` (mit Jupyter),
`rollback-vor-b` (vor der Abhängigkeitsaktualisierung).

## Offene Punkte

- RAM-Ausstattung des Servers (1,8 GB) weit unter Richtwert; die
  Swap-Erweiterung auf 9 GiB (zusätzliches `/swapfile2`, 8 GB, in
  `/etc/fstab`) ist ein Workaround, kein Ersatz für ein VPS-Upgrade.
  GM-Lauf und Forecast liefen damit durch, aber langsam und zulasten
  der übrigen Container (Swap-Druck).
- `sendMessage.php` und `generateApiKey.php` antworten 500 (privates
  `mail_helper.php` fehlt upstream); MySQL-abhängiger API-Key-Teil bis
  Etappe E außer Betrieb (akzeptiert, siehe docs/web_inventory.md).
- ~~Apache im Container startet nicht automatisch nach Container-/Server-
  Neustart~~ — erledigt 2026-07-11: Container mit Restart-Policy
  `unless-stopped` neu angelegt, `scripts/container_start.sh` startet
  Apache idempotent im Vordergrund (Auslöser: 502 nach Server-Reboot).

## PostgreSQL-Betrieb (seit Etappe E, 2026-07-13)

Service `paraglidable-db` (postgis, digest-gepinnt, nur im Compose-Netz,
`mem_limit 384m`, kleine Puffer — der Server hat 1,8 GB RAM). Zugangsdaten
in `.env` (Vorlage `.env.example`; Datei liegt nur auf dem Server).

```bash
# Migrationen (Alembic, Schema Nr. 1 aufwärts)
docker compose run --rm -w /app/db web alembic upgrade head

# Vergleichsjob Datei<->DB von Hand (läuft sonst nach jedem Worker-Lauf)
docker exec paraglidable-worker python3 pipeline/verify_db_mirror.py

# Sicherung (Betriebsdaten sind reproduzierbar bis auf accounts/api_keys!)
docker exec paraglidable-db pg_dump -U paraglidable -d paraglidable \
  -t accounts -t api_keys > backup_api_keys.sql
```

Merkposten: Prognosedaten in der DB sind Spiegel (aus Dateien
reproduzierbar, Aufbewahrung 8 Läufe) — **einzig `accounts`/`api_keys`
sind Originaldaten** und gehören in die Server-Sicherung.
