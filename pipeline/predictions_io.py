# Reader/writer for the forecast->tiler interchange format predictions.txt.
# Specification: docs/predictions_format.md (stage C1 of the modernization).
#
# Behavior-preserving by construction: writing back a parsed file reproduces
# it byte for byte (verified against the golden-master reference in
# pipeline/tests/test_predictions_io.py). Pure stdlib, Python 3.6+.

from collections import namedtuple

# Column semantics, see docs/predictions_format.md.
PRESSURE_LEVELS_HPA = (1000, 900, 800, 700, 600)
NUM_VALUES = 28

V_GEOPOTENTIAL = slice(0, 5)    # geopotential height per level [gpm]
V_FLYABILITY = slice(5, 10)     # flyability per level [0..1]
V_CROSSABILITY = 10             # crossability, mean over levels [0..1]
V_WIND_PREDICTED = slice(11, 16)  # predicted wind per level
V_HUMIDITY = 16                 # humidity, mean over levels
V_ATTRACTIVENESS = 17           # reserved, always 0.0
V_WIND_U = slice(18, 23)        # GRIB wind U per level [m/s]
V_WIND_V = slice(23, 28)        # GRIB wind V per level [m/s]

PredictionCell = namedtuple("PredictionCell", ["lat", "lon", "values"])


def read_predictions(path):
	"""Parse a predictions.txt file into a list of PredictionCell.

	Mirrors MapData::readFile in tiler/Tiler/main.cpp: fields are separated
	by a single space, lines with fewer than 3 fields are skipped, the
	number of value fields is taken as-is.
	"""
	cells = []
	with open(path, "r") as f:
		for line in f:
			fields = line.rstrip("\n").split(" ")
			if len(fields) < 3:
				continue
			cells.append(PredictionCell(
				lat=float(fields[0]),
				lon=float(fields[1]),
				values=[float(v) for v in fields[2:]],
			))
	return cells


def write_predictions(path, cells):
	"""Write cells in the exact format of GridLatLon.export_data_for_tiler:
	every field C-"%f" formatted (fixed, 6 decimals), single-space separated,
	one trailing newline per line."""
	with open(path, "w") as f:
		for cell in cells:
			fields = [cell.lat, cell.lon] + list(cell.values)
			f.write(" ".join("%f" % v for v in fields) + "\n")
