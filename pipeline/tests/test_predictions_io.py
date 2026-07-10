# Round-trip tests for pipeline/predictions_io.py against the format spec
# (docs/predictions_format.md). Run inside the container:
#   python -m unittest discover -s pipeline/tests -v

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pipeline.predictions_io import (read_predictions, write_predictions,
									 PredictionCell, NUM_VALUES)

REFERENCE = "/workspaces/Paraglidable/golden_master/reference/predictions.txt"


class TestSynthetic(unittest.TestCase):

	def test_round_trip_synthetic(self):
		cells = [
			PredictionCell(21.75, -11.5, [float(i) / 7.0 for i in range(NUM_VALUES)]),
			PredictionCell(-3.125, 42.875, [0.0] * NUM_VALUES),
		]
		with tempfile.TemporaryDirectory() as d:
			p1 = os.path.join(d, "a.txt")
			p2 = os.path.join(d, "b.txt")
			write_predictions(p1, cells)
			write_predictions(p2, read_predictions(p1))
			with open(p1, "rb") as f1, open(p2, "rb") as f2:
				self.assertEqual(f1.read(), f2.read())

	def test_short_lines_skipped(self):
		with tempfile.TemporaryDirectory() as d:
			p = os.path.join(d, "a.txt")
			with open(p, "w") as f:
				f.write("1.0 2.0\n")           # only 2 fields: skipped
				f.write("1.0 2.0 3.0\n")       # minimal valid line
				f.write("\n")                  # empty: skipped
			cells = read_predictions(p)
			self.assertEqual(len(cells), 1)
			self.assertEqual(cells[0].values, [3.0])


@unittest.skipUnless(os.path.isfile(REFERENCE),
					 "golden-master reference not available")
class TestReference(unittest.TestCase):

	def test_round_trip_reference_byte_identical(self):
		cells = read_predictions(REFERENCE)
		self.assertEqual(len(cells), 33666)
		for c in cells:
			self.assertEqual(len(c.values), NUM_VALUES)
		with tempfile.TemporaryDirectory() as d:
			p = os.path.join(d, "roundtrip.txt")
			write_predictions(p, cells)
			with open(REFERENCE, "rb") as f1, open(p, "rb") as f2:
				self.assertEqual(f1.read(), f2.read())


if __name__ == "__main__":
	unittest.main()
