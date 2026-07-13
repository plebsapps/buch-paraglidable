# CLAUDE.md

Arbeitsregeln für KI-Sitzungen in diesem Repository. Sie gelten verbindlich
für jede Änderung — unabhängig davon, auf welcher Maschine gearbeitet wird.

## Projektkontext

Dieses Repository ist ein GPLv3-Derivat von Paraglidable (Antoine Meler,
github.com/AntoineMeler/Paraglidable) und zugleich der reale Praxisfall für
Teil II des Buchs „Softwaremodernisierung mit KI" (Untertitel: „Bestandssysteme
kontrolliert erneuern, mit Sicherheitsnetz, kleinen Schritten und
nachprüfbaren Ergebnissen").
Ziel: verhaltenserhaltende Modernisierung — Portierung von Tiler (C++/Qt)
und Webschicht (PHP) nach Python, PostgreSQL für Ergebnisse und Metadaten,
Docker Compose, Betrieb auf **paraglidable.plebsapps.de**.

Der vollständige Etappenplan mit Zielarchitektur, Entscheidungen und
aktuellem Stand steht in **docs/plan.md** — vor jeder Arbeit lesen.

## Verbindliche Regeln

1. **Verhaltenserhalt ist die Leitplanke.** Das Prognoseverhalten ändert
   sich nicht. Der Golden-Master-Vergleich muss vor jedem Merge/Push grün
   sein: `golden_master/compare_golden_master.py` gegen
   `golden_master/reference/` (siehe golden_master/README.md).
2. **Toleranzen nie stillschweigend ändern.** Jede Änderung der
   Vergleichstoleranzen ist ein eigener Commit mit Begründung.
3. **Kleine, einzeln rücknehmbare Commits.** Conventional-Commit-Präfix
   (feat/fix/docs/chore); jede Reparatur am Bestand ein eigener Commit,
   dessen Botschaft die Ursache erklärt (die Historie erzählt den Umbau).
4. **Keine unbeauftragten Mitverbesserungen.** Erkannte Verbesserungen als
   Vorschlagsliste melden, nicht nebenbei umsetzen.
5. **Training ist außer Scope.** Die `.npy`-Gewichte in
   `neural_network/bin/models/` sind ein unersetzliches, eingefrorenes
   Artefakt; kein Neutraining, keine Modelländerung.
6. **Original-Copyrights unantastbar.** LICENSE und bestehende
   Copyright-Hinweise bleiben; wesentliche Änderungen in NOTICE nachführen
   (GPLv3 §5a).
7. **LF-Zeilenenden.** `.gitattributes` erzwingt LF; unter Windows
   `core.autocrlf=false` setzen und niemals CRLF einführen (Shell-Skripte
   laufen in Linux-Containern).

## Umgebung aufsetzen (frische Maschine)

```bash
git clone https://github.com/plebsapps/buch-paraglidable
cd buch-paraglidable

# Große Datenpakete (nicht in Git): GM-Referenz + Eingabe, Trainingsdaten,
# Elevation, Corner-Cache (eingefrorenes Artefakt des entfernten C++-Tilers)
gh release download golden-master-v1 --pattern '*.tar.gz'
tar -xzf gm_reference.tar.gz    # golden_master/input + golden_master/reference
tar -xzf gm_data.tar.gz         # neural_network/bin/data + tiler/_cache/elevation
tar -xzf gm_corner_cache.tar.gz # tiler/_cache/256 (ohne ihn rechnet der
                                # Python-Tiler die Ecken langsam selbst)

docker build -t paraglidable ./docker/
docker run -d --name paraglidable -p 8001:80 \
  -v "$PWD:/workspaces/Paraglidable" paraglidable tail -f /dev/null
```

## Prüfbefehle (vor jedem Push grün)

```bash
# Golden-Master-Lauf auf eingefrorener Eingabe + Vergleich
docker exec -e PYTHONHASHSEED=0 paraglidable \
  python /workspaces/Paraglidable/golden_master/run_golden_master.py \
  /workspaces/Paraglidable/golden_master/runs/check
docker exec paraglidable \
  python /workspaces/Paraglidable/golden_master/compare_golden_master.py \
  /workspaces/Paraglidable/golden_master/reference \
  /workspaces/Paraglidable/golden_master/runs/check

# Unit-Tests (Format-Naht u. a.)
docker exec -w /workspaces/Paraglidable paraglidable \
  python -m unittest discover -s pipeline/tests -v
```

## Wichtige Dokumente

- `docs/plan.md` — Etappenplan A–E, Zielarchitektur, Entscheidungen, Stand
- `docs/predictions_format.md` — Spezifikation der forecast→tiler-Naht
- `golden_master/README.md` — eingefrorene Referenz, Toleranzen, Nutzung
- `NOTICE` — Herkunft und wesentliche Änderungen (GPLv3)
