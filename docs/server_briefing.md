# Briefing: Etappe S — Server-Inbetriebnahme (paraglidable.plebsapps.de)

Scopevertrag für die erste KI-Sitzung auf dem Ubuntu-Server. Vorher lesen:
`CLAUDE.md` (Arbeitsregeln) und `docs/plan.md` (Etappenstand). Es gelten
insbesondere: minimaler Eingriff, Stoppregel bei Unklarheit, Toleranzen des
Golden-Master-Vergleichs niemals eigenmächtig ändern.

## Auftrag

Das Repository auf diesem Server in Betrieb nehmen: Setup nach CLAUDE.md,
Golden Master auf dieser Hardware verifizieren, die bestehende Webschicht
über den vorhandenen Reverse Proxy unter **https://paraglidable.plebsapps.de**
mit TLS-Zertifikat und **Basic-Auth** erreichbar machen, einen manuellen
Forecast-Lauf durchführen, Befunde dokumentieren.

**Nicht Teil des Auftrags:** Portierungsarbeit (Etappen C2–E), Cron/Scheduler
(kommt mit D3 als APScheduler), MySQL-Aufbau (kommt mit E), Änderungen an
Pipeline- oder Vergleichscode, Toleranzänderungen.

Vom Betreiber bereits erledigt: DNS-Eintrag paraglidable.plebsapps.de → dieser
Server; `gh auth login`; Docker und Reverse Proxy laufen bereits für andere
Subdomains.

## Schritt 1 — Bestandsaufnahme (nur lesen, nichts ändern)

Erheben und in `docs/deployment.md` (neu anlegen) festhalten:

- Architektur: `uname -m` — **muss x86_64 sein** (das gepinnte
  TensorFlow-Image existiert nicht für ARM). Sonst: STOPP, berichten.
- Ressourcen: RAM (Richtwert ≥ 8 GB gesamt), freier Plattenplatz
  (Richtwert ≥ 15 GB: Image ~4 GB, Release-Daten ~1,5 GB entpackt, Läufe/Kacheln).
  Deutlich darunter: STOPP, berichten.
- Docker-Version, Compose vorhanden?
- Welcher Reverse Proxy läuft (nginx, Caddy, Traefik, …), wie sind die
  bestehenden plebsapps.de-Subdomains konfiguriert, wie beziehen sie ihre
  Zertifikate (certbot, eingebautes ACME, …)? Nur lesen, Muster verstehen.
- DNS-Check: `dig +short paraglidable.plebsapps.de` zeigt die Server-IP.

## Schritt 2 — Setup nach CLAUDE.md

Exakt die Befehle aus CLAUDE.md „Umgebung aufsetzen (frische Maschine)",
mit **einer bewussten Abweichung**: Der Container-Port wird nur an localhost
gebunden, weil der Reverse Proxy TLS terminiert:

```bash
docker run -d --name paraglidable -p 127.0.0.1:8001:80 \
  -v "$PWD:/workspaces/Paraglidable" paraglidable tail -f /dev/null
```

Falls `gh release download` das Release nicht findet (mehrere Remotes):
`gh release download golden-master-v1 -R plebsapps/buch-paraglidable --pattern '*.tar.gz'`.

## Schritt 3 — Verifikation: Golden Master auf dieser Hardware

Prüfbefehle aus CLAUDE.md (GM-Lauf, Vergleich, Unit-Tests). Erwartung:
**grün innerhalb der kalibrierten Toleranzen** (dritte Hardware nach
Entwicklungsrechner und GitHub-CI; die Toleranzen wurden genau für
Hardware-Drift kalibriert, siehe golden_master/README.md).

Falls rot: Ursache untersuchen und mit echten Ausgaben berichten —
**nicht wiederholen bis grün, nicht Toleranzen weiten, nicht stummschalten.**
Der Befund ist wertvolles Material (Buchkapitel 18.4).

Echte Ausgaben (Vergleichs-Summary, Testanzahl) in `docs/deployment.md`
protokollieren.

## Schritt 4 — Webschicht über den Reverse Proxy

1. Apache im Container starten: `docker exec -w /workspaces/Paraglidable/scripts paraglidable sh start_server.sh`
   Kurztest: `curl -s http://127.0.0.1:8001/ | head` liefert die Startseite.
2. HTTP-Snapshots gegen den laufenden Container prüfen:
   `golden_master/snapshot_www.py --check` (13 Snapshots, siehe golden_master/README.md).
3. Im vorhandenen Proxy-System (Muster der anderen Subdomains folgen):
   vhost/Route `paraglidable.plebsapps.de` → `http://127.0.0.1:8001`,
   TLS-Zertifikat auf dem dort üblichen Weg (Let's Encrypt),
   **Basic-Auth verpflichtend davor** (ein Benutzer reicht; Zugangsdaten dem
   Betreiber nennen, nicht ins Repo committen).
   Begründung Basic-Auth: Die Legacy-Webschicht (PHP 7.2 auf Ubuntu 18.04 im
   eingefrorenen Container) bleibt bis zur Portierung (D2) geschützt.
4. Bekannte, akzeptierte Grenzen (nicht „reparieren"): `sendMessage.php` und
   `generateApiKey.php` antworten 500 (privates mail_helper.php fehlt
   upstream); der MySQL-abhängige API-Key-Teil bleibt bis Etappe E außer
   Betrieb (docs/web_inventory.md).

## Schritt 5 — Ein manueller Forecast-Lauf

Einen aktuellen GFS-Zyklus laden und die Pipeline einmal von Hand ausführen
(`scripts/download_GFS.py`, dann Forecast wie in scripts/cron_tasks/
update_forecasts.sh, aber manuell — **keinen Cron einrichten**), damit die
Seite unter der neuen Domain aktuelle Daten zeigt. Bei NOMADS-Problemen
(Rate-Limit, Ausfall): Rückfall auf den archivierten GM-Zyklus 2026-07-09 06z
und als offenen Punkt notieren.

## Schritt 6 — Abschluss

- `docs/deployment.md` vervollständigen: Serverbefund, Proxy-Integration
  (welche Datei/Route), Zertifikatsweg, Startbefehle, offene Punkte.
- `docs/plan.md`: Etappe S auf ✅ mit Datum und Einzeiler-Befund.
- Kleine, getrennte Commits (Conventional-Commit-Präfix), pushen.
- Abschlussbericht an den Betreiber: was läuft, echte Prüf-Ausgaben,
  Zugangsdaten-Hinweis, Vorschlagsliste (erkannte, nicht beauftragte
  Verbesserungen).
