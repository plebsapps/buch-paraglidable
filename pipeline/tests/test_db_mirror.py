# -*- coding: utf-8 -*-
"""Charakterisierung des DB-Spiegels (Etappe E, Expand).

Läuft bewusst OHNE Datenbank und ohne psycopg2 — genau so, wie der
eingefrorene Legacy-Container und der GM-Runner das Modul sehen:
1. Ohne PARAGLIDABLE_DB_URL ist jede Funktion ein No-op (kein Import
   von psycopg2, kein Verbindungsversuch).
2. Das COPY-Format der Zellen-Ingestion entspricht exakt der
   predictions.txt-Zeile (Feldtexte unverändert, docs/predictions_format.md).
"""

import os
import tempfile
import unittest

from pipeline import db


class FakeCursor(object):
	"""Fängt copy_from/execute ab — kein psycopg2 nötig."""

	def __init__(self):
		self.copied = None
		self.executed = []

	def execute(self, sql, params=None):
		self.executed.append((sql, params))

	def copy_from(self, buf, table, columns):
		self.copied = (buf.read(), table, columns)


class TestNoopWithoutUrl(unittest.TestCase):

	def setUp(self):
		self._saved = os.environ.pop("PARAGLIDABLE_DB_URL", None)

	def tearDown(self):
		if self._saved is not None:
			os.environ["PARAGLIDABLE_DB_URL"] = self._saved

	def test_all_entry_points_are_noops(self):
		self.assertFalse(db.enabled())
		# Kein Attributzugriff auf das (fehlende) forecast-Objekt, kein
		# psycopg2-Import — sonst würde hier eine Exception fliegen.
		db.mirror_day(None, "2026070906", "2026-07-09")
		db.finish_runs()
		db.close_dangling(1)
		db.prune_runs()


class TestCellCopyFormat(unittest.TestCase):

	def test_copy_lines_mirror_predictions_line(self):
		line1 = "45.100000 6.200000 " + " ".join(["0.123456"] * 28)
		line2 = "45.200000 6.300000 " + " ".join(["0.654321"] * 28)
		with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
			f.write(line1 + "\n" + line2 + "\n")
			path = f.name
		try:
			cur = FakeCursor()
			db._ingest_cells(cur, 7, "2026-07-09", path)
			data, table, columns = cur.copied
			self.assertEqual(table, "cell_forecasts")
			self.assertEqual(columns,
			                 ("run_id", "valid_date", "cell_id", "lat", "lon", "values"))
			rows = data.rstrip("\n").split("\n")
			self.assertEqual(len(rows), 2)
			f0 = rows[0].split("\t")
			self.assertEqual(f0[0], "7")
			self.assertEqual(f0[1], "2026-07-09")
			self.assertEqual(f0[2], "0")
			# Feldtexte unverändert aus der Datei übernommen
			self.assertEqual(f0[3], "45.100000")
			self.assertEqual(f0[4], "6.200000")
			self.assertEqual(f0[5], "{" + ",".join(["0.123456"] * 28) + "}")
			self.assertEqual(rows[1].split("\t")[2], "1")
			# vorher wird der (run, Tag) geleert — Idempotenz
			self.assertIn("DELETE FROM cell_forecasts", cur.executed[0][0])
		finally:
			os.unlink(path)


if __name__ == "__main__":
	unittest.main()
