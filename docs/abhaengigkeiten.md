# Abhängigkeiten: Stand, Aktualisierung, Restliste (Etappe B/G)

Stand: 2026-07-15. Etappe B des Plans (`docs/plan.md`) war bis dahin nicht
ausgeführt: Etappe A hatte auf die bewährten Stände gepinnt, aktualisiert
wurde danach nichts. Dieses Dokument holt das nach und hält fest, was
bewegt wurde, was nicht, und warum.

Verfahren nach dem Drehbuch: ein Paket oder eine technisch untrennbare
Gruppe pro Schritt, nach jedem Schritt der volle Nachweis, eigener Commit.
Reihenfolge nach SE06: Sicherheit zuerst, dann nach Risiko, die
numerischen und ML-nahen Bibliotheken zuletzt.

## Erstinventur (2026-07-14)

Ermittelt über die Schwachstellendatenbank OSV (Abfrage je Paket/Version)
und `pip-audit`:

| Baum | Laufzeit | Pakete | Pakete mit Befunden | Befunde |
|---|---|---|---|---|
| Web (`web/requirements.txt`) | Python 3.11 | 6 direkt | 1 (starlette) | 8 |
| Pipeline (`docker/python_requirements.lock.txt`) | Python 3.6.9 / Ubuntu 18.04 | 115 | 26 | 961 |

Die 961 Befunde des Pipeline-Baums verteilen sich sehr ungleich:
tensorflow 2.1.0 trägt 743, Pillow 8.4.0 dreißig, der Jupyter-Stack
(jupyter-server, jupyterlab, notebook, nbconvert, mistune, tornado,
Werkzeug, Jinja2, bleach …) zusammen rund siebzig.

## Aktualisiert

| Schritt | Paket(e) | Von | Auf | Wirkung | Nachweis |
|---|---|---|---|---|---|
| B1 | fastapi (zieht starlette) | 0.115.6 (starlette 0.41.3) | 0.139.0 (starlette 1.3.1) | 8 Befunde → 0 | 13/13 Aufzeichnungen EQUIVALENT |
| B2 | uvicorn | 0.34.0 | 0.51.0 | keine Befunde, Stand gepflegt | 13/13 EQUIVALENT |
| B3 | SQLAlchemy + alembic | 2.0.36 / 1.14.0 | 2.0.51 / 1.18.5 | keine Befunde, Stand gepflegt | 13/13 EQUIVALENT + Migrationskette bis 0003 (head) |
| B4 | psycopg2-binary | 2.9.10 | 2.9.12 | keine Befunde, Stand gepflegt | 13/13 EQUIVALENT |
| B5 | requests + urllib3 + certifi (untrennbar) | 2.22.0 / 1.25.7 / 2019.11.28 | 2.27.1 / 1.26.20 / 2025.4.26 | 35 Befunde → 18; TLS-Vertrauensspeicher 6,6 Jahre erneuert | Golden Master EQUIVALENT + echter TLS-Abruf gegen NOAA |

Zu B5 gehört die neue Pflicht-Abhängigkeit `charset-normalizer==2.0.12`
(requests ≥ 2.26 ersetzt damit chardet); nach SE05 geprüft: keine
bekannten Befunde. B5 heilt nebenbei einen bestehenden Defekt: Im Image
war `idna 3.10` installiert, obwohl `requests 2.22.0` `idna<2.9` verlangt.
`pip check` meldet seither einen konsistenten Baum.

**Ehrlich zu B5:** `requests` selbst gewinnt nichts (8 Befunde vorher wie
nachher). Seine Fixes verlangen Python 3.7+ und sind auf 3.6 unerreichbar.
Angehoben wurde es als Türöffner — `requests 2.22.0` pinnt `urllib3<1.26`,
ohne den Schritt wäre urllib3 nicht bewegbar.

## Restliste: bewusst zurückgestellt

Jeder Eintrag hat Begründung und Wiedervorlage. Zurückstellen ist eine
Entscheidung, kein Vergessen.

| Paket | Stand | Befunde | Begründung | Wiedervorlage |
|---|---|---|---|---|
| tensorflow | 2.1.0 | 743 | Laufzeit des eingefrorenen Modellartefakts. Ein Sprung ändert mit hoher Wahrscheinlichkeit das Prognoseverhalten und verletzt damit die Leitplanke (VK01); beurteilen ließe sich die Abweichung nur mit reproduzierbarem Training, das nicht gesichert ist (docs/plan.md, Kapitel 10.3.2 des Buchs). Zudem Python-3.6-Grenze. | Nur zusammen mit einer fachlichen Freigabe für ein neues Prognoseverhalten. Kein Termin. |
| Pillow | 8.4.0 | 30 | 8.4.0 ist die letzte Fassung mit Python-3.6-Unterstützung. Nicht bewegbar ohne Basisimage-Wechsel. | Mit dem Basisimage (siehe unten). |
| numpy | 1.18.1 | 6 | An tensorflow 2.1.0 gebunden. | Mit tensorflow. |
| scipy | 1.4.1 | 2 | An tensorflow 2.1.0 gebunden. | Mit tensorflow. |
| protobuf | 3.11.2 | 7 | An tensorflow 2.1.0 gebunden. | Mit tensorflow. |
| urllib3 | 1.26.20 | 10 (Rest) | Die verbleibenden Fixes verlangen urllib3 2.x und damit Python 3.8+. | Mit dem Basisimage. |
| requests | 2.27.1 | 8 (Rest) | Fixes verlangen Python 3.7+. | Mit dem Basisimage. |
| ~~Jupyter-Stack~~ | ~~div.~~ | ~~108~~ | **Erledigt 2026-07-15.** Kein Produktivcode benutzte ihn: Das Original-Dockerfile installierte `jupyter` für den Notebook-Ablauf des Autors, Etappe B fror ihn samt rund 50 Folgepaketen ins Lockfile ein. Nicht aktualisiert, sondern entfernt — 128 → 63 Pakete, 996 → 888 Befunde, Image 5,78 → 5,56 GB, Golden Master EQUIVALENT bei unveränderten Toleranzen. | — |

## Die eine Ursache

Alle offenen Einträge hängen an derselben Wurzel: dem Basisimage
`tensorflow/tensorflow:latest-py3` (Digest gepinnt) = TensorFlow 2.1.0,
Ubuntu 18.04, Python 3.6.9. Python 3.6 ist seit Dezember 2021 ohne
Pflege, Ubuntu 18.04 seit April 2023. Solange dieses Image die Laufzeit
des eingefrorenen Modells ist, ist die Decke fest.

## Gemessener Endstand (2026-07-15)

Am Produktionsimage selbst gemessen, nicht am Lockfile gerechnet (das
Image enthält zusätzlich die apt-verwalteten Pakete):

| | Pakete | mit Befunden | Befunde |
|---|---|---|---|
| vor Etappe B/G | 128 | 32 | 996 |
| nach B1–B5 und der Entrümpelung | **63** | **21** | **888** |

Von den 888 trägt TensorFlow 2.1.0 allein 743. Die Entrümpelung hat
nebenbei sichtbar gemacht, was vorher im Rauschen lag: Nach Jupyter sind
die größten verbliebenen Posten apt-verwaltete Pakete des Basisimages —
`cryptography 2.1.4` (19), `pip 19.3.1` (14), `setuptools 44.0.0` (7),
`pycrypto 2.6.1` (4). Auch sie hängen am Basisimage; das Lockfile
erreicht sie nicht.

Der Wechsel des Basisimages ist kein Abhängigkeitsschritt, sondern eine
fachliche Entscheidung über das Prognoseverhalten. Er gehört damit nicht
in Etappe B, sondern vor die Fachseite.

## Erledigt: basemap (2026-07-15)

Beim Import-Test der Jupyter-Entrümpelung gefunden, aber **vorbestehend**:
Der Dockerfile installierte `basemap` (gepinnt aus einem GitHub-Archiv),
und der Import scheiterte seit matplotlib 3.3.4 an
`matplotlib.cbook.dedent`. Aufgefallen ist es nie, denn **keine `.py`-Datei
im Repository importiert basemap**. Seine einzige Nutzung sind das
Dokumentations-Notebook des Autors und ein README-Auszug, die damit die
Trainingszellen-Karte zeichnen — beide brauchen Jupyter, das im selben
Zug ging. Entfernt samt `pyshp` (basemap-exklusiv). `pyproj` **bleibt**:
Es sieht wie ein basemap-Anhängsel aus, wird aber von `pygrib` gebraucht.

Wirkung: 63 → 61 Pakete, Image 5,56 → **4,96 GB** (basemap bringt
Küstenlinien- und Grenzdaten in mehreren Auflösungen mit). Keine
Sicherheitsbefunde — basemap hatte null; reine Entrümpelung. Golden
Master EQUIVALENT bei unveränderten Toleranzen, Unit-Tests 17/17.

## Offen: numba und llvmlite

Verwaist wie basemap, aber ein eigener Fall: Das Original-Dockerfile
installierte `numba` in derselben Zeile wie `jupyter`; nichts im
Repository importiert es, `llvmlite` ist sein Unterbau. Null
Sicherheitsbefunde, aber llvmlite ist ein dicker Brocken. Nächster
Kandidat derselben Logik; eigener Auftrag, offen.
