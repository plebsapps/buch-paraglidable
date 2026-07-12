# Web-Inventar (Etappe C3)

Vollständiges Inventar der Apache/PHP-Webschicht (`www/`) als Grundlage der
FastAPI-Portierung (Etappe D2). Jeder Endpunkt wird vor der Portierung per
Charakterisierungstest (HTTP-Snapshot gegen das laufende Original) eingefroren.

## Rewrite-Regeln (.htaccess)

| Datei | Regel |
|---|---|
| `www/.htaccess` | `api.paraglidable.com/*` → `https://paraglidable.com/apps/api/get.php$1` |
| `www/apps/api/.htaccess` | `Options -Indexes` |

## Endpunkte

### 1. `GET /apps/api/get.php` — der zentrale Vorhersage-Endpunkt

CORS: `Access-Control-Allow-Origin: *`. Drei Nutzungsarten:

- **API-Modus** (`key` gesetzt, hex-validiert): liest die Spotliste des
  Schlüssels aus MySQL (`ApiKeys.latLonName`, serialisiertes PHP-Array),
  liefert für 10 Tage je Spot `fly`/`XC` (aus `.data`-Kacheln, Zoom 7) und
  ggf. `takeoff` (aus `spots.json`). Ausgabe `format=json` (Standard) oder
  `xml`; `htmlentities=1` liefert HTML-escaped Text statt Content-Type.
- **Kachel-Pixel-Modus** (`tx,ty,x,y,zoom,date`): liest die Werte eines
  Pixels aus `data/tiles/<date>/256/<zoom>/<tx>/<ty>.data`, Ausgabe als
  kommaseparierte Werte; `elev=1` hängt `;<elevation>` an (aus `.elev`);
  `spot=<id>` hängt die Takeoff-Flyability aus `spots.json` an.
- **Lat/Lon-Modus** (`lat,lon,date`): wie Pixel-Modus, Koordinaten werden
  per WebMercator-Mathe (`math.php`, fest Zoom 7) in Kachel/Pixel übersetzt.

Fehlerverhalten: fehlende Kacheldatei → leere Antwort (`die("")`);
unbekannter/nicht-hex Schlüssel → `unknown key`.

### 2. `GET /apps/api/generateApiKey.php`

`email` + `lat_i/lon_i/name_i/spotId_i`-Serie → legt `Accounts`-Zeile an,
erzeugt Schlüssel (`md5(rand())` XOR Konstante), `REPLACE INTO ApiKeys`,
verschickt Mail mit Schlüssel. Antwort `1` oder `Error`.

### 3. `POST /apps/sendMessage.php`

Kontaktformular: `name,email,text` → Mail an den Autor. Antwort `1`/`Error`.
Googlebot wird ignoriert.

### 4. `GET /apps/search.php?q=`

Proxy auf `http://localhost:8001/q/<q>.js` (Spot-Suchindex als statische
JS-Dateien), nur mit Referer paraglidable.com/.net; Eingabe wird von
Sonderzeichen bereinigt.

### 5. `GET /apps/api/getAnalysisData.php`

Honeypot/Abwehr: prüft Host, Referer und Cookie; verdächtige Zugriffe werden
in `banned.txt.php` dauerhaft gebannt und erhalten deterministisch gefälschte
Daten (`srand` aus Datum), legitime einen Redirect auf statische
Analyse-Daten (`data/data_2013-01-01`).

### 6. `GET /apps/gtag.php`

Proxy für das Google-Analytics-Skript (nicht auf localhost).

### 7. Statische Auslieferung

`index.html`, `mobile.html`, `mobileAndroid.html`, `css/`, `js/`, `imgs/`
sowie die vom Prognoselauf erzeugten Daten: `data/tiles/<date>/256/...`
(PNG-Kacheln **und** `.data`-Dateien), `data/tiles/<date>/spots.json`,
`progress.txt`, `data/elevation/<zoom>/<tx>/<ty>.elev`.

## Binärformate der Webschicht

- **`.data`** (vom C++-Tiler erzeugt, von get.php gelesen): pro Kachel
  256×256 Pixel × `nbVals` Bytes, Wert = `round(byte/255, 4)`;
  Pixelindex = `x*256 + y`. Teil der D1-Portierung!
- **`.elev`**: pro Pixel uint16 big-endian, Index `2*(x*256+y)`.

## Datenbank des Originals (MySQL, localhost)

Zugang root/paraglidable (hartkodiert in `bdd.php`), DB `paraglidable`:
`Accounts(id, email)`, `ApiKeys(account, apiKey, latLonName)` mit
PHP-serialisierter Spotliste. Wandert in Etappe E nach PostgreSQL
(Tabellen `accounts`, `api_keys`; Zugang per Umgebungsvariablen).

## Charakterisierungstests

`golden_master/snapshot_www.py` friert 13 HTTP-Snapshots gegen das laufende
Original ein (`record`/`check`; Snapshots in `golden_master/www_snapshots/`).
Befund dabei: **`www/apps/mail_helper.php` ist upstream nicht committet**
(vermutlich wegen SMTP-Zugangsdaten) — `sendMessage.php` und
`generateApiKey.php` antworten daher in jedem frischen Klon mit HTTP 500;
die Snapshots frieren genau diesen beobachtbaren Zustand ein.
`getAnalysisData.php` ist bewusst ausgenommen (verändert bei jedem Aufruf
die versionierte Bann-Liste `banned.txt.php`).

## Portierungsentscheidungen (entschieden 2026-07-11, umgesetzt in D2)

1. **gtag.php / Google Analytics:** 1:1 portiert (snapshot-treu); Entfernen/
   Ersetzen des Trackings ist eine Identitätsfrage → Etappe F.
   *Nachtrag F Teil 1 (2026-07-12): Tracking entfernt — gtag-Bootstrap aus
   allen HTML-Seiten, Endpunkt aus web/app.py (jetzt 404), PHP-Quelle
   gelöscht; Snapshot gtag_localhost friert den 404 ein.*
2. **Honeypot getAnalysisData.php:** bewusst **nicht** portiert → 404. War
   schon von den Charakterisierungstests ausgenommen und hängt an nicht
   versionierten Daten und veränderlichem Bann-Zustand.
3. **Mail-Versand** (Kontaktformular, API-Schlüssel): der eingefrorene
   500-Zustand bleibt erhalten; API-Schlüssel brauchen die Datenbank →
   Etappe E. *Nachtrag F Teil 1 (2026-07-12): Das Kontaktformular wurde aus
   dem Frontend entfernt (Kontakt läuft über ralfwbalz.ch); ein eigener
   SMTP-Versand ist damit vom Tisch. Der sendMessage-Endpunkt bleibt als
   eingefrorener 500-Stub.*
4. **search.php:** beobachtbares Verhalten 1:1 erhalten (Referer-Prüfung,
   Bereinigung, Proxy-Versuch → leere Antwort); direkte Auslieferung erst,
   wenn ein Suchindex existiert.
