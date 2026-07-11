# coding: utf-8
# Parser-level tests for the pipeline CLI (stage C2). The heavy forecast
# machinery (TensorFlow) is imported only inside the commands, so these
# tests stay cheap. Run inside the container:
#   python -m unittest discover -s pipeline/tests -v

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pipeline.cli import build_parser


class TestCliParser(unittest.TestCase):

	def setUp(self):
		self.parser = build_parser()

	def test_subcommands_dispatch(self):
		for argv in (["run"],
		             ["download", "--cycle", "2026070906"],
		             ["forecast", "--date", "2026-07-09"],
		             ["tile", "--date", "2026-07-09"],
		             ["publish", "--date", "2026-07-09", "--cycle", "2026070906"]):
			args = self.parser.parse_args(argv)
			self.assertTrue(callable(args.func), argv)

	def test_download_requires_cycle(self):
		with self.assertRaises(SystemExit):
			self.parser.parse_args(["download"])

	def test_path_overrides_default_to_legacy(self):
		args = self.parser.parse_args(["forecast", "--date", "2026-07-09"])
		self.assertIsNone(args.grib_dir)
		self.assertIsNone(args.predictions)
		self.assertIsNone(args.tiles_dir)

	def test_meteo_files_collected(self):
		args = self.parser.parse_args(
			["forecast", "--date", "2026-07-09", "--meteo-files", "a", "b", "c"])
		self.assertEqual(args.meteo_files, ["a", "b", "c"])


if __name__ == "__main__":
	unittest.main()
