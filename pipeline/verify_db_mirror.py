# -*- coding: utf-8 -*-
"""Vergleichsjob Datei <-> DB (Etappe E, Migrate-Vorstufe).

Expand and Contract verlangt vor jeder Leser-Umstellung den Nachweis,
dass beide Formate denselben Inhalt tragen. Dieser Job prüft je Tag
eines Laufs:

 * Zellen: Re-Serialisierung der DB-Zeilen im exakten Dateiformat
   (docs/predictions_format.md, "%f"-Felder) und Vergleich des SHA-256
   mit dem beim Spiegeln festgehaltenen Fingerabdruck der Quelldatei —
   die Datei selbst ist flüchtig (/tmp), der Fingerabdruck nicht.
 * Spots: Feldvergleich gegen die persistente spots.json des Tages
   (Werte exakt: Gleitkomma beidseitig aus demselben Text geparst).

Aufruf (im worker-Container, PARAGLIDABLE_DB_URL gesetzt):
    python3 pipeline/verify_db_mirror.py [--run-id N]
Exit-Code 0 = EQUIVALENT, 1 = Abweichung/kein Lauf.
"""

import argparse
import hashlib
import json
import os
import sys

ROOT = "/workspaces/Paraglidable"


def _connect():
	import psycopg2
	return psycopg2.connect(os.environ["PARAGLIDABLE_DB_URL"])


def verify_cells(cur, run_id, strdate, expected_sha):
	cur.execute(
		"SELECT cell_id, lat, lon, values FROM cell_forecasts "
		"WHERE run_id=%s AND valid_date=%s ORDER BY cell_id",
		(run_id, strdate))
	sha = hashlib.sha256()
	count = 0
	for cell_id, lat, lon, values in cur:
		line = " ".join("%f" % v for v in [lat, lon] + list(values)) + "\n"
		sha.update(line.encode("ascii"))
		count += 1
	return sha.hexdigest() == expected_sha, count


def verify_spots(cur, run_id, strdate):
	path = os.path.join(ROOT, "www/data/tiles", strdate, "spots.json")
	if not os.path.exists(path):
		return None, 0  # Tag bereits aufgeräumt — nicht prüfbar, kein Fehler
	with open(path) as f:
		features = json.load(f)["features"]
	file_spots = {}
	for feat in features:
		p = feat["properties"]
		lon, lat = feat["geometry"]["coordinates"]
		file_spots[int(p["id"])] = (p["name"], lat, lon, int(p["nbFlights"]),
		                            float(p["flyability"]))
	cur.execute(
		"SELECT s.id, s.name, s.lat, s.lon, s.nb_flights, f.flyability "
		"FROM spot_forecasts f JOIN spots s ON s.id = f.spot_id "
		"WHERE f.run_id=%s AND f.valid_date=%s", (run_id, strdate))
	db_spots = {row[0]: tuple(row[1:]) for row in cur}
	return file_spots == db_spots, len(db_spots)


def verify_run(run_id=None):
	conn = _connect()
	try:
		cur = conn.cursor()
		if run_id is None:
			cur.execute("SELECT id FROM forecast_runs WHERE status='ok' "
			            "ORDER BY id DESC LIMIT 1")
			row = cur.fetchone()
			if row is None:
				print("kein abgeschlossener Lauf in der DB")
				return False
			run_id = row[0]
		cur.execute("SELECT valid_date, predictions_sha256 FROM tile_sets "
		            "WHERE run_id=%s ORDER BY valid_date", (run_id,))
		days = cur.fetchall()
		if not days:
			print("Lauf %s hat keine Tage" % run_id)
			return False
		ok = True
		for valid_date, expected_sha in days:
			strdate = valid_date.strftime("%Y-%m-%d")
			cells_ok, n_cells = verify_cells(cur, run_id, strdate, expected_sha)
			spots_ok, n_spots = verify_spots(cur, run_id, strdate)
			spots_txt = ("uebersprungen (Datei fehlt)" if spots_ok is None
			             else ("OK" if spots_ok else "ABWEICHUNG"))
			print("[%s] run %s: %d Zellen %s, %d Spots %s" % (
				strdate, run_id, n_cells,
				"OK" if cells_ok else "ABWEICHUNG", n_spots, spots_txt))
			ok = ok and cells_ok and (spots_ok is not False)
		print("RESULT: %s" % ("EQUIVALENT" if ok else "DIFFERENT"))
		return ok
	finally:
		conn.close()


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
	parser.add_argument("--run-id", type=int, default=None)
	args = parser.parse_args()
	if not os.environ.get("PARAGLIDABLE_DB_URL"):
		sys.exit("PARAGLIDABLE_DB_URL ist nicht gesetzt")
	sys.exit(0 if verify_run(args.run_id) else 1)
