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

## Offene Punkte

- RAM-Ausstattung des Servers (1,8 GB) weit unter Richtwert; Swap-Erweiterung
  ist ein Workaround, kein Ersatz für ein VPS-Upgrade.
