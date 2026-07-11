# coding: utf-8
# PHP-faithful helper functions for the FastAPI port of the web layer
# (stage D2). Each function reproduces the exact observable semantics of
# the PHP 7.2 construct it replaces -- including the quirks. Pure stdlib,
# importable (and unit-tested) inside the frozen Python 3.6 container.

import math
import re
import string

_INT_RE = re.compile(r"^[+-]?[0-9]+$")


def php_filter_int(value):
	"""filter_var($v, FILTER_VALIDATE_INT): int or None (PHP: false).
	Missing parameters (None) validate to None like PHP's null."""
	if value is None:
		return None
	value = value.strip()
	if not _INT_RE.match(value):
		return None
	return int(value)


def php_filter_float(value):
	"""filter_var($v, FILTER_VALIDATE_FLOAT): float or None (PHP: false)."""
	if value is None:
		return None
	value = value.strip()
	try:
		f = float(value)
	except ValueError:
		return None
	if math.isnan(f) or math.isinf(f):  # PHP rejects NAN/INF strings
		return None
	return f


def ctype_xdigit(s):
	return len(s) > 0 and all(c in string.hexdigits for c in s)


def php_round4(x):
	"""round($x, 4) for x >= 0: round half away from zero."""
	return math.floor(x * 10000.0 + 0.5) / 10000.0


def php_float_str(v):
	"""PHP float-to-string with default precision=14 (used by implode/echo).
	Integers print without decimal point: 1.0 -> '1', 0.0 -> '0'."""
	if isinstance(v, int):
		return str(v)
	return "%.14G" % v


def php_substr_byte(contents, idx):
	"""ord(substr($contents, $idx, 1)) for a bytes buffer, with PHP substr
	semantics: index past the end -> false -> ord('') == 0; negative index
	counts from the end; below -strlen it clamps to 0."""
	length = len(contents)
	if idx >= length:
		return 0
	if idx < 0:
		idx = 0 if idx < -length else length + idx
	return contents[idx]


def php_substr2_be(contents, off):
	"""(ord(s[0]) << 8) + ord(s[1]) for $s = substr($contents, $off, 2),
	with the same out-of-range semantics as php_substr_byte (a short or
	empty slice contributes 0 for the missing bytes)."""
	length = len(contents)
	if off >= length:
		return 0  # substr -> false; ord of '' is 0 for both bytes
	if off < 0:
		off = 0 if off < -length else length + off
	b0 = contents[off]
	b1 = contents[off + 1] if off + 1 < length else 0
	return (b0 << 8) + b1


def php_loose_eq_int(value, number):
	"""PHP 7 loose comparison $value == $number for a JSON value against an
	int: numeric strings compare numerically, non-numeric strings compare
	as 0 (PHP 7 semantics, changed only in PHP 8)."""
	if isinstance(value, (int, float)):
		return float(value) == float(number)
	m = re.match(r"^[ \t\n]*[+-]?([0-9]*\.?[0-9]+([eE][+-]?[0-9]+)?)?", str(value))
	num = m.group(0).strip() if m else ""
	try:
		return float(num) == float(number)
	except ValueError:
		return 0.0 == float(number)


# --- math.php ---------------------------------------------------------------

ORIGIN_SHIFT = 2.0 * math.pi * 6378137.0 / 2.0
INITIAL_RESOLUTION = 2.0 * math.pi * 6378137.0


def latlon_to_tile_coords(lat, lon, data_tiles_zoom=7):
	"""Port of LatLonToTileCoords (math.php): WebMercator at fixed zoom 7,
	intval() truncation, x/y clamped to [0, 255]."""
	# LatLonToMeters(-lat, lon)
	mx = lon * ORIGIN_SHIFT / 180.0
	my = math.log(math.tan((90.0 + (-lat)) * math.pi / 360.0)) / (math.pi / 180.0)
	my = my * ORIGIN_SHIFT / 180.0
	res = INITIAL_RESOLUTION / (2.0 ** data_tiles_zoom)
	px = (mx + ORIGIN_SHIFT) / res
	py = (my + ORIGIN_SHIFT) / res
	x = max(0, min(255, int(math.fmod(px, 1) * 256.0)))
	y = max(0, min(255, int(math.fmod(py, 1) * 256.0)))
	return {"tx": int(px), "ty": int(py), "x": x, "y": y, "zoom": data_tiles_zoom}


# --- search.php input cleaning ----------------------------------------------

SEARCH_STRIP = ("q/", ".js", "/", "\\", ",", ";", "'", "\"", ".")


def clean_search_q(q):
	"""str_replace([...], '', $q) -- sequential, order matters."""
	for tok in SEARCH_STRIP:
		q = q.replace(tok, "")
	return q
