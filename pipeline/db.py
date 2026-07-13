# -*- coding: utf-8 -*-
"""PostgreSQL-Spiegel der Vorhersageergebnisse (Etappe E, Expand-Phase).

Expand and Contract, Phase 1: Die Pipeline schreibt ihre Ergebnisse
zusätzlich in die Datenbank; alle Leser arbeiten unverändert auf den
Dateien. Deshalb gilt hier durchgehend:

 * Jede Funktion ist ein No-op, solange PARAGLIDABLE_DB_URL nicht
   gesetzt ist. Golden-Master-Läufe und der Legacy-Container setzen die
   Variable nicht — ihr Verhalten ist beweisbar unverändert.
 * psycopg2 wird erst innerhalb der Funktionen importiert; der
   eingefrorene Legacy-Container (ohne psycopg2) kann dieses Modul
   gefahrlos importieren.
 * Fehler beim Spiegeln brechen den Prognoselauf nicht ab (der
   Aufrufer fängt sie und warnt) — die Dateien bleiben der Pfad.

Läuft mit Python 3.6 (eingefrorenes Pipeline-Image).
"""

import hashlib
import io
import json
import os

# Lauf-Zeilen dieses Prozesses: GFS-Zyklus -> forecast_runs.id
_run_ids = {}

ROOT = "/workspaces/Paraglidable"
KEEP_RUNS = 8  # Aufbewahrung: ~2 Tage bei 4 Zyklen/Tag (job_clean)


def enabled():
	return bool(os.environ.get("PARAGLIDABLE_DB_URL"))


def _connect():
	import psycopg2
	return psycopg2.connect(os.environ["PARAGLIDABLE_DB_URL"])


def _git_sha():
	"""HEAD ohne git-Binary auflösen (wie pipeline/scheduler.py, job commit)."""
	try:
		git_dir = os.path.join(ROOT, ".git")
		with open(os.path.join(git_dir, "HEAD")) as f:
			head = f.read().strip()
		if not head.startswith("ref: "):
			return head
		ref = head[5:]
		ref_path = os.path.join(git_dir, ref)
		if os.path.exists(ref_path):
			with open(ref_path) as f:
				return f.read().strip()
		with open(os.path.join(git_dir, "packed-refs")) as f:
			for line in f:
				if line.strip().endswith(ref):
					return line.split(" ")[0]
	except (IOError, OSError):
		pass
	return None


def _ensure_run(cur, gfs_cycle):
	if gfs_cycle in _run_ids:
		return _run_ids[gfs_cycle]
	cur.execute(
		"INSERT INTO forecast_runs (gfs_cycle, code_git_sha, params) "
		"VALUES (%s, %s, %s) RETURNING id",
		(gfs_cycle, _git_sha(), json.dumps({"quelle": "worker"})))
	run_id = cur.fetchone()[0]
	_run_ids[gfs_cycle] = run_id
	return run_id


def _ingest_cells(cur, run_id, strdate, predictions_path):
	"""predictions.txt -> cell_forecasts, per COPY (33 666 Zeilen je Tag).

	Die Feldtexte werden unverändert an PostgreSQL übergeben; float8
	parst dieselbe Dezimaldarstellung wie Python float() — der
	Vergleichsjob (pipeline/verify_db_mirror.py) weist die Treue nach."""
	buf = io.StringIO()
	sha = hashlib.sha256()
	with open(predictions_path, "rb") as f:
		for cell_id, raw in enumerate(f):
			sha.update(raw)
			fields = raw.decode("ascii").rstrip("\n").split(" ")
			if len(fields) < 3:
				continue
			buf.write("%d\t%s\t%d\t%s\t%s\t{%s}\n" % (
				run_id, strdate, cell_id, fields[0], fields[1],
				",".join(fields[2:])))
	buf.seek(0)
	cur.execute(
		"DELETE FROM cell_forecasts WHERE run_id=%s AND valid_date=%s",
		(run_id, strdate))
	cur.copy_from(buf, "cell_forecasts",
	              columns=("run_id", "valid_date", "cell_id", "lat", "lon", "values"))
	return sha.hexdigest()


def _ingest_spots(cur, run_id, strdate, spots_json_path):
	with open(spots_json_path, "r") as f:
		features = json.load(f)["features"]
	for feat in features:
		props = feat["properties"]
		lon, lat = feat["geometry"]["coordinates"]
		cur.execute(
			"INSERT INTO spots (id, name, lat, lon, nb_flights) "
			"VALUES (%s, %s, %s, %s, %s) "
			"ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, "
			"lat=EXCLUDED.lat, lon=EXCLUDED.lon, nb_flights=EXCLUDED.nb_flights",
			(int(props["id"]), props["name"], lat, lon, int(props["nbFlights"])))
		cur.execute(
			"INSERT INTO spot_forecasts (run_id, spot_id, valid_date, flyability) "
			"VALUES (%s, %s, %s, %s) "
			"ON CONFLICT (run_id, spot_id, valid_date) "
			"DO UPDATE SET flyability=EXCLUDED.flyability",
			(run_id, int(props["id"]), strdate, float(props["flyability"])))


def mirror_day(forecast, gfs_cycle, strdate):
	"""Einen veröffentlichten Tag spiegeln (Aufrufer: step_publish)."""
	if not enabled():
		return
	conn = _connect()
	try:
		with conn:
			with conn.cursor() as cur:
				run_id = _ensure_run(cur, gfs_cycle)
				pred_sha = _ingest_cells(cur, run_id, strdate,
				                         forecast.prediction_filename_for_tiler)
				_ingest_spots(cur, run_id, strdate,
				              os.path.join(forecast.tiles_dir, strdate, "spots.json"))
				cur.execute(
					"INSERT INTO tile_sets (run_id, valid_date, zoom_min, zoom_max, "
					"base_path, predictions_sha256) VALUES (%s, %s, %s, %s, %s, %s)",
					(run_id, strdate, forecast.min_tiles_zoom,
					 forecast.max_tiles_zoom,
					 "www/data/tiles/%s/256" % strdate, pred_sha))
	finally:
		conn.close()


def finish_runs():
	"""Lauf-Zeilen dieses Prozesses abschließen (Aufrufer: Ende von main())."""
	if not enabled() or not _run_ids:
		return
	conn = _connect()
	try:
		with conn:
			with conn.cursor() as cur:
				for run_id in _run_ids.values():
					cur.execute(
						"UPDATE forecast_runs SET status='ok', finished_at=now() "
						"WHERE id=%s AND status='running'", (run_id,))
	finally:
		conn.close()


def close_dangling(exit_code):
	"""Nach Subprozess-Ende liegengebliebene 'running'-Zeilen schließen
	(Aufrufer: scheduler.job_forecast; greift nur nach Abstürzen)."""
	if not enabled():
		return
	conn = _connect()
	try:
		with conn:
			with conn.cursor() as cur:
				cur.execute(
					"UPDATE forecast_runs SET status=%s, finished_at=now(), exit_code=%s "
					"WHERE status='running'",
					("ok" if exit_code == 0 else "failed", exit_code))
	finally:
		conn.close()


def prune_runs(keep=KEEP_RUNS):
	"""Alte Läufe entfernen (Aufrufer: scheduler.job_clean); Kinder-Zeilen
	fallen per ON DELETE CASCADE mit."""
	if not enabled():
		return
	conn = _connect()
	try:
		with conn:
			with conn.cursor() as cur:
				cur.execute(
					"DELETE FROM forecast_runs WHERE id NOT IN "
					"(SELECT id FROM forecast_runs ORDER BY id DESC LIMIT %s)",
					(keep,))
	finally:
		conn.close()
