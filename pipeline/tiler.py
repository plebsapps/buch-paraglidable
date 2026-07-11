# coding: utf-8
# Python port of the C++/Qt Tiler (tiler/Tiler/main.cpp), stage D1 of the
# modernization. Behavior-preserving: reads the same tilerArguments.json,
# the same corner cache and elevation cache, and writes the same outputs
# (PNG tiles + _transpa versions, vignette.png, zoom-7 .data tiles, legend
# images, progress file). Verified by a full pixel comparison of every
# tile against the C++ output on identical predictions.txt input
# (golden_master/compare_tiler_outputs.py).
#
# Faithfulness notes (quirks preserved on purpose, see main.cpp):
#   - float32 arithmetic in the same evaluation order as the C++ float code;
#     lat/lon are narrowed from double to float32 like the C++
#     std::pair<float,float> latlon.
#   - drawBordersUsingHisto applies its darkening once per dx iteration of
#     the 3x3 neighborhood scan, with the pixel re-read each time, so a
#     pixel can be darkened up to 3 times cumulatively (with integer
#     truncation after each step). Ported as three sequential passes.
#   - getElevationValueInElevationTile is indexed with the *global* pixel
#     coordinates of the vignette (x up to 790); out-of-range lookups
#     return elevation 0 like the C++ bounds check.
#   - .data tiles contain bytes only for pixels whose 4 cell corners were
#     found; other pixels are skipped entirely.
#   - The mountainess tiles are loaded by the C++ code but only used in
#     disabled debug branches; they are not read here at all.
#
# Usage:  python3 pipeline/tiler.py <tilerArguments.json>

import json
import math
import os
import struct
import sys

import numpy as np
from PIL import Image

TILE_RESOLUTION = 256
ALPHA_VALUE = 160

F32 = np.float32
F64 = np.float64

# ============================================================================
# tilesmath.cpp (double precision throughout)
# ============================================================================

ORIGIN_SHIFT = 2.0 * math.pi * 6378137.0 / 2.0
INITIAL_RESOLUTION = 2.0 * math.pi * 6378137.0


def resolution(zoom):
	return INITIAL_RESOLUTION / (2.0 ** zoom)


def pixels_to_meters(px, py, zoom):
	res = resolution(zoom)
	return px * res - ORIGIN_SHIFT, py * res - ORIGIN_SHIFT


def meters_to_latlon(mx, my):
	lon = (mx / ORIGIN_SHIFT) * 180.0
	lat = (my / ORIGIN_SHIFT) * 180.0
	lat = 180.0 / math.pi * (2.0 * np.arctan(np.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
	return -lat, lon


def latlon_to_meters(lat, lon):
	mx = lon * ORIGIN_SHIFT / 180.0
	my = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
	my = my * ORIGIN_SHIFT / 180.0
	return mx, my


def meters_to_pixels(mx, my, zoom):
	res = resolution(zoom)
	return (mx + ORIGIN_SHIFT) / res, (my + ORIGIN_SHIFT) / res


def tile_pixel_to_latlon(dx, dy, zoom):
	"""dx, dy: float64 arrays of tile coordinates. Returns float32 lat/lon
	(the C++ narrows the double result into std::pair<float,float>)."""
	mx, my = pixels_to_meters(dx, dy, zoom)
	lat, lon = meters_to_latlon(mx, my)
	return lat.astype(F32), lon.astype(F32)


# ============================================================================
# MapData (main.cpp): predictions.txt via the C1 seam, values as float32
# ============================================================================

class MapData(object):

	def __init__(self, filename):
		sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
		from pipeline.predictions_io import read_predictions
		cells = read_predictions(filename)
		self.lat = np.array([c.lat for c in cells], dtype=F32)
		self.lon = np.array([c.lon for c in cells], dtype=F32)
		self.vals = np.array([c.values for c in cells], dtype=F32)  # (N, 28)
		self.min_lat = float(self.lat.min())
		self.max_lat = float(self.lat.max())
		self.min_lon = float(self.lon.min())
		self.max_lon = float(self.lon.max())

	def find_cell_corners(self, lat, lon):
		"""Brute-force corner search, port of MapData::findCellCorners.
		Ties in the distance sort follow numpy's stable argsort; std::sort
		is unstable, so at exact ties the result may differ -- in practice
		corners come from the frozen cache (see load_or_compute_corners)."""
		epsilon = 0.00001
		res = [-1, -1, -1, -1]  # mLatmLon, mLatpLon, pLatmLon, pLatpLon
		if not (self.min_lat - epsilon <= lat <= self.max_lat + epsilon and
				self.min_lon - epsilon <= lon <= self.max_lon + epsilon):
			return res
		d = (self.lat - F32(lat)) ** 2 + (self.lon - F32(lon)) ** 2
		closest = np.argsort(d, kind="stable")[:8]
		for idp in closest:
			clat, clon = self.lat[idp], self.lon[idp]
			if clat <= lat:
				if clon <= lon and res[0] < 0:
					res[0] = int(idp)
				if clon >= lon and res[1] < 0:
					res[1] = int(idp)
			if clat >= lat:
				if clon <= lon and res[2] < 0:
					res[2] = int(idp)
				if clon >= lon and res[3] < 0:
					res[3] = int(idp)
		return res


def between_corners(lat, lon, c_lat, c_lon):
	return (c_lat[0] <= lat and c_lon[0] <= lon and
			c_lat[1] <= lat and c_lon[1] >= lon and
			c_lat[2] >= lat and c_lon[2] <= lon and
			c_lat[3] >= lat and c_lon[3] >= lon)


def compute_corners_scalar(map_data, lat_arr, lon_arr, shifts):
	"""Sequential port of the corner search in drawTile (cache-miss path),
	including the shift-guessing optimization and its shared `shifts` list."""
	n = lat_arr.shape[0]
	out = np.empty((n, 4), dtype=np.int32)
	corners = None
	npoints = map_data.lat.shape[0]
	for i in range(n):
		lat = float(lat_arr[i])
		lon = float(lon_arr[i])
		if corners is not None and -1 not in corners:
			c_lat = map_data.lat[corners]
			c_lon = map_data.lon[corners]
			inside = between_corners(lat, lon, c_lat, c_lon)
		else:
			inside = False
		if corners is None or not inside:
			found = False
			if corners is not None and -1 not in corners:
				for s in shifts:
					nc = [c + s for c in corners]
					if any(c < 0 or c >= npoints for c in nc):
						continue
					if between_corners(lat, lon, map_data.lat[nc], map_data.lon[nc]):
						corners = nc
						found = True
						break
				if not found:
					corners0_avant = corners[0]
					corners = map_data.find_cell_corners(lat, lon)
					if -1 not in corners:
						shifts.append(corners[0] - corners0_avant)
			else:
				corners = map_data.find_cell_corners(lat, lon)
		out[i, :] = corners
	return out


def load_or_compute_corners(cache_dir, zoom, tx, ty, x_min, x_max, y_min, y_max,
							map_data, lat_arr, lon_arr, shifts):
	"""Port of the corner cache block in drawTile: read the int32 big-endian
	cache file if it exists and is non-empty, otherwise compute the corners
	and commit the cache via _TMP + rename."""
	cache_file = "%s/%d/%d/%d/%d_%d_%d_%d_%d" % (
		cache_dir, TILE_RESOLUTION, zoom, tx, ty, x_min, x_max, y_min, y_max)
	n = (x_max - x_min) * (y_max - y_min)
	if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0:
		corners = np.fromfile(cache_file, dtype=">i4")
		return corners.reshape((n, 4)).astype(np.int32)
	print("[tiler] corner cache miss, computing:", cache_file)
	corners = compute_corners_scalar(map_data, lat_arr, lon_arr, shifts)
	cache_parent = os.path.dirname(cache_file)
	if not os.path.isdir(cache_parent):
		os.makedirs(cache_parent)
	tmp = cache_file + "_TMP"
	corners.astype(">i4").tofile(tmp)
	if os.path.exists(cache_file):
		os.remove(cache_file)
	os.rename(tmp, cache_file)
	return corners


# ============================================================================
# Elevation tiles (elevation.cpp): int16 big-endian, x-major, missing = 0
# ============================================================================

def load_elevation_tile(cache_dir, zoom, tx, ty):
	filename = "%s/elevation/%d/%d/%d.elev" % (cache_dir, zoom, tx, ty)
	if not os.path.isfile(filename):
		return None  # empty data means all zeros
	return np.fromfile(filename, dtype=">i2").astype(np.int32)


def elevation_values(elev_data, x_arr, y_arr):
	"""Port of getElevationValueInElevationTile including its bounds check:
	out-of-range coordinates (vignette!) return 0."""
	out = np.zeros(x_arr.shape[0], dtype=np.int32)
	if elev_data is None:
		return out
	valid = ((x_arr >= 0) & (x_arr < TILE_RESOLUTION) &
			 (y_arr >= 0) & (y_arr < TILE_RESOLUTION))
	idx = x_arr[valid] * TILE_RESOLUTION + y_arr[valid]
	out[valid] = elev_data[idx]
	return out


# ============================================================================
# ValToColor (main.cpp)
# ============================================================================

VTC_VALS = [F32(0.0), F32(0.5), F32(1.0)]
VTC_COLORS = [(0xA0, 0x00, 0x00), (0xA0, 0x70, 0x00), (0x00, 0xA0, 0x00)]


def val_to_color(val):
	"""Vectorized port of ValToColor::getColor. val: float32 array.
	Returns (r, g, b) uint8 arrays."""
	v = np.clip(val, VTC_VALS[0], VTC_VALS[-1])
	r = np.zeros(v.shape, dtype=np.int64)
	g = np.zeros(v.shape, dtype=np.int64)
	b = np.zeros(v.shape, dtype=np.int64)
	done = np.zeros(v.shape, dtype=bool)
	for k in range(len(VTC_VALS) - 1):
		sel = (~done) & (v <= VTC_VALS[k + 1])
		if not sel.any():
			continue
		interp = ((v[sel] - VTC_VALS[k]) / (VTC_VALS[k + 1] - VTC_VALS[k])).astype(F32)
		c0 = VTC_COLORS[k]
		c1 = VTC_COLORS[k + 1]
		# C++: (float32 mult + int) stays float32, then + 0.5 promotes to
		# double, then (int) truncates
		for ch, dst in ((0, r), (1, g), (2, b)):
			t32 = (interp * (c1[ch] - c0[ch]) + c0[ch]).astype(F32)
			dst[sel] = np.floor(t32.astype(F64) + 0.5).astype(np.int64)
		done |= sel
	return r, g, b


# ============================================================================
# Fufu pattern (main.cpp drawFufu)
# ============================================================================

def draw_fufu(rgba, xs, ys, val):
	"""Vectorized port of drawFufu. rgba: (n, 4) int arrays view; xs, ys:
	pixel coordinates within the image; val: float32 array."""
	freq = 16.0
	rx = xs.astype(F64)
	ry = ys.astype(F64)
	mag64 = (np.sin((rx / float(TILE_RESOLUTION)) * (2.0 * math.pi) * freq) *
			 np.sin((ry / float(TILE_RESOLUTION)) * (2.0 * math.pi) * freq))
	# smoothstep(fabs(mag)*val, 0, 1): the argument is computed in double
	# (fabs(mag) double * float val) and narrowed to float32 by the call
	x = (np.abs(mag64) * val.astype(F64)).astype(F32)
	t = np.clip(x, F32(0.0), F32(1.0))
	# t*t*(3.0 - 2.0*t): (t*t) float32, (3.0 - 2.0*t) double, product double,
	# narrowed to float32 by the return
	mag = ((t * t).astype(F64) * (3.0 - 2.0 * t.astype(F64))).astype(F32)
	mag64 = mag.astype(F64)
	# RGB blends in double ((1.0-mag) promotes), alpha stays float32
	for ch in range(3):
		c = rgba[:, ch].astype(F64)
		rgba[:, ch] = np.floor((1.0 - mag64) * c + mag64 * 255.0).astype(np.int64)
	a = rgba[:, 3]
	a32 = (a.astype(F32) + (255 - a).astype(F32) * mag).astype(F32)
	rgba[:, 3] = np.floor(a32.astype(F64)).astype(np.int64)


# ============================================================================
# Borders (main.cpp loadGeoJson / fillBordersHistoTile / drawBordersUsingHisto)
# ============================================================================

def load_geojson(filename):
	"""Port of loadGeoJson including its traversal order: for MultiPolygon
	features the inner rings are appended while iterating, the (empty)
	outer accumulator is appended afterwards only if it has > 1 points."""
	all_lines = []
	if not filename:
		return all_lines
	with open(filename, "r") as f:
		doc = json.load(f)
	for country in doc.get("features", []):
		geo = country.get("geometry", {}).get("coordinates", [])
		for igeo_part in geo:
			line = []
			for pt in igeo_part:
				first = pt[0]
				if isinstance(first, list):  # one nesting level deeper
					inner = [(p2[1], p2[0]) for p2 in pt]
					if len(inner) > 1:
						all_lines.append(inner)
				else:
					line.append((pt[1], pt[0]))
			if len(line) > 1:
				all_lines.append(line)
	return all_lines


def convert_borders_coords(borders, zoom):
	converted = []
	for line in borders:
		pts = []
		for lat, lon in line:
			mx, my = latlon_to_meters(-lat, lon)
			pts.append(meters_to_pixels(mx, my, zoom))
		converted.append(pts)
	return converted


def fill_borders_histo(borders, tx, ty):
	"""Port of fillBordersHistoTile: DDA rasterization of the border
	segments into a per-pixel histogram. histo[(px, py)] = [(bl, sl), ...]"""
	histo = {}
	for bl, line in enumerate(borders):
		for sl in range(1, len(line)):
			x1 = F32((line[sl - 1][0] - tx) * TILE_RESOLUTION - 0.5)
			y1 = F32((line[sl - 1][1] - ty) * TILE_RESOLUTION - 0.5)
			x2 = F32((line[sl][0] - tx) * TILE_RESOLUTION - 0.5)
			y2 = F32((line[sl][1] - ty) * TILE_RESOLUTION - 0.5)
			if ((x1 < 0 and x2 < 0) or
					(x1 >= TILE_RESOLUTION and x2 >= TILE_RESOLUTION) or
					(y1 < 0 and y2 < 0) or
					(y1 >= TILE_RESOLUTION and y2 >= TILE_RESOLUTION)):
				continue
			if abs(x2 - x1) >= abs(y2 - y1):
				longueur = abs(x2 - x1)
			else:
				longueur = abs(y2 - y1)
			dx = F32((x2 - x1) / longueur)
			dy = F32((y2 - y1) / longueur)
			x = F32(x1 + F32(0.5))
			y = F32(y1 + F32(0.5))
			i = 0
			while i <= longueur:
				px = int(x)
				py = int(y)
				if 0 <= px < TILE_RESOLUTION and 0 <= py < TILE_RESOLUTION:
					histo.setdefault((px, py), []).append((bl, sl - 1))
				x = F32(x + dx)
				y = F32(y + dy)
				i += 1
	return histo


def distance_point_segment(px, py, x1, y1, x2, y2):
	"""Vectorized float32 port of distancePointSegment. px, py: arrays."""
	sx = F32(x2 - x1)
	sy = F32(y2 - y1)
	ux = (px - F32(x1)).astype(F32)
	uy = (py - F32(y1)).astype(F32)
	dp = (sx * ux + sy * uy).astype(F32)
	sn2 = F32(sx * sx + sy * sy)
	# distances for the three regimes
	d_start = np.sqrt(ux * ux + uy * uy).astype(F32)
	vx = (px - F32(x2)).astype(F32)
	vy = (py - F32(y2)).astype(F32)
	d_end = np.sqrt(vx * vx + vy * vy).astype(F32)
	ah2 = (dp * dp / sn2).astype(F32)
	un2 = (ux * ux + uy * uy).astype(F32)
	with np.errstate(invalid="ignore"):
		d_seg = np.sqrt(un2 - ah2).astype(F32)
	return np.where(dp < 0, d_start, np.where(dp > sn2, d_end, d_seg)).astype(F32)


def draw_borders_using_histo(rgba_flat, borders, tx, ty, width, height):
	"""Port of drawBordersUsingHisto with its quirks: the loops run over
	x, y in [0, TILE_RESOLUTION) even when the image is larger (vignette),
	and the (minDist, bls) condition is evaluated and applied after each
	dx column of the 3x3 neighborhood scan, re-reading the pixel -- so a
	pixel can be darkened up to 3 times cumulatively, with integer
	truncation after each step. rgba_flat: (width*height, 4) x-major."""
	if not borders:
		return
	histo = fill_borders_histo(borders, tx, ty)
	if not histo:
		return
	line_width = 1.65

	# Region the C++ code actually touches (always 256x256).
	rw = min(TILE_RESOLUTION, width)
	rh = min(TILE_RESOLUTION, height)
	nreg = rw * rh

	# For every region pixel and every dx pass: min distance and which
	# border lines were seen (cell (cx, cy) is visited by pixel
	# (cx-dx, cy-dy) in the pass for dx).
	min_dist = np.full((3, nreg), F32(1000.0))
	bl_ids = sorted(set(bl for segs in histo.values() for bl, _sl in segs))
	bl_index = {bl: i for i, bl in enumerate(bl_ids)}
	bl_seen = np.zeros((3, len(bl_ids), nreg), dtype=bool)

	for (cx, cy), segs in histo.items():
		for dxi, dx in enumerate((-1, 0, 1)):
			x0 = cx - dx
			if x0 < 0 or x0 >= rw:
				continue
			ys_valid = [cy - dy for dy in (1, 0, -1) if 0 <= cy - dy < rh]
			if not ys_valid:
				continue
			pix = [x0 * rh + y0 for y0 in ys_valid]
			pxa = np.full(len(pix), x0, dtype=F32)
			pya = np.array(ys_valid, dtype=F32)
			for bl, sl in segs:
				line = borders[bl]
				x1 = F32((line[sl][0] - tx) * TILE_RESOLUTION - 0.5)
				y1 = F32((line[sl][1] - ty) * TILE_RESOLUTION - 0.5)
				x2 = F32((line[sl + 1][0] - tx) * TILE_RESOLUTION - 0.5)
				y2 = F32((line[sl + 1][1] - ty) * TILE_RESOLUTION - 0.5)
				dist = distance_point_segment(pxa, pya, x1, y1, x2, y2)
				# C++ takes the min via `if (dist < minDist)`, which is
				# false for NaN (degenerate segments) -- np.fmin matches
				# that; np.minimum would propagate the NaN.
				np.fmin.at(min_dist, (dxi, pix), dist)
				bl_seen[dxi, bl_index[bl], pix] = True

	# Sequential dx passes with cumulative state, like the C++ loop.
	cum_min = np.full(nreg, F32(1000.0))
	cum_seen = np.zeros((len(bl_ids), nreg), dtype=bool)
	# map region pixel index -> flat image index
	reg_x = np.repeat(np.arange(rw), rh)
	reg_y = np.tile(np.arange(rh), rw)
	img_idx = reg_x * height + reg_y
	for dxi in range(3):
		cum_min = np.fmin(cum_min, min_dist[dxi])
		cum_seen |= bl_seen[dxi]
		nbls = cum_seen.sum(axis=0)
		cond = (cum_min < line_width) & (nbls > 1)
		if not cond.any():
			continue
		sel = img_idx[cond]
		# (0.25*minDist/lineWidth + 0.75): double (0.25 promotes)
		factor = 0.25 * cum_min[cond].astype(F64) / line_width + 0.75
		for ch in range(3):
			rgba_flat[sel, ch] = np.floor(rgba_flat[sel, ch] * factor).astype(np.int64)
		rgba_flat[sel, 3] = ALPHA_VALUE


# ============================================================================
# Pixel value computation (the big #else branch in drawTile)
# ============================================================================

def interpolate_altitude(pression, vals5):
	"""Vectorized port of interpolateAltitude. pression: float32 array,
	vals5: (n, 5) float32. Everything float32."""
	fidx = ((F32(1000.0) - pression) / F32(100.0)).astype(F32)
	max_idx = 4
	fidx = np.clip(fidx, F32(0.0), F32(float(max_idx)))
	idx0 = np.clip(fidx.astype(np.int32), 0, max_idx)
	idx1 = np.clip(fidx.astype(np.int32) + 1, 0, max_idx)
	n = np.arange(vals5.shape[0])
	v0 = vals5[n, idx0]
	v1 = vals5[n, idx1]
	frac = (fidx - idx0.astype(F32)).astype(F32)
	interp = (frac * v1 + (F32(1.0) - frac) * v0).astype(F32)
	return np.where(idx0 != idx1, interp, v0).astype(F32)


def nivellement_barometrique(z, geo_alt):
	"""Port of the geopotentials variant: z (n,) float32 altitude,
	geo_alt (n, 5) float32 altitudes for the levels 1000..600 hPa."""
	levels = np.array([1000.0, 900.0, 800.0, 700.0, 600.0], dtype=F32)
	n = z.shape[0]
	out = np.empty(n, dtype=F32)
	below = z <= geo_alt[:, 0]
	above = z >= geo_alt[:, 4]
	out[below] = levels[0]
	out[above] = levels[4]
	mid = ~(below | above)
	if mid.any():
		zm = z[mid]
		gm = geo_alt[mid]
		res = np.empty(zm.shape[0], dtype=F32)
		done = np.zeros(zm.shape[0], dtype=bool)
		for kp in range(4):  # first kp with z <= alt[kp+1]
			sel = (~done) & (zm <= gm[:, kp + 1])
			if not sel.any():
				continue
			z0 = gm[sel, kp]
			z1 = gm[sel, kp + 1]
			p0 = levels[kp]
			p1 = levels[kp + 1]
			interp = ((z0 - zm[sel]) / (z0 - z1)).astype(F32)
			res[sel] = (interp * p1 + (F32(1.0) - interp) * p0).astype(F32)
			done |= sel
		res[~done] = F32(0.0)
		out[mid] = res
	return out


def linear_interpolation(lat, lon, c_lat, c_lon, c_vals):
	"""Vectorized float32 port of linearInterpolation.
	lat, lon: (n,) float32; c_lat, c_lon: (n, 4); c_vals: (n, 4, 28)."""
	dx = (lon - c_lon[:, 0]).astype(F32)[:, None]
	dy = (lat - c_lat[:, 0]).astype(F32)[:, None]
	Dx = (c_lon[:, 1] - c_lon[:, 0]).astype(F32)[:, None]
	Dy = (c_lat[:, 2] - c_lat[:, 0]).astype(F32)[:, None]
	v0 = c_vals[:, 0, :]
	Dfx = (c_vals[:, 1, :] - v0).astype(F32)
	Dfy = (c_vals[:, 2, :] - v0).astype(F32)
	Dfxy = (v0 + c_vals[:, 3, :] - c_vals[:, 1, :] - c_vals[:, 2, :]).astype(F32)
	# Dfx*dx/Dx + Dfy*dy/Dy + Dfxy*dx*dy/(Dx*Dy) + v0, left to right
	t1 = (Dfx * dx / Dx).astype(F32)
	t2 = (Dfy * dy / Dy).astype(F32)
	t3 = (Dfxy * dx * dy / (Dx * Dy)).astype(F32)
	return (t1 + t2 + t3 + v0).astype(F32)


def compute_wind_angles(c_vals_interp):
	"""Port of the windAngles unwrapping loop. Input: (n, 28) float32."""
	n = c_vals_interp.shape[0]
	angles = np.empty((n, 5), dtype=F32)
	for alt in range(5):
		u = c_vals_interp[:, 18 + alt]
		v = c_vals_interp[:, 23 + alt]
		angle = np.arctan2(v, u).astype(F32)
		if alt > 0:
			prev = angles[:, alt - 1].astype(F64)
			a64 = angle.astype(F64)
			angle = np.where(prev < a64 - math.pi, (a64 - 2.0 * math.pi),
							 np.where(prev > a64 + math.pi, (a64 + 2.0 * math.pi),
									  a64)).astype(F32)
		angles[:, alt] = angle
	return angles


def quantize_byte(val):
	"""(uchar)qMax(0, qMin(255, (int)(0.5 + val*255.0f))): val*255 in
	float32, + 0.5 promotes to double, (int) truncates, then clamp."""
	x = np.floor((val.astype(F32) * F32(255.0)).astype(F64) + 0.5)
	return np.clip(x, 0, 255).astype(np.uint8)


# ============================================================================
# drawTile
# ============================================================================

class TileRenderer(object):

	def __init__(self, args, map_data, borders):
		self.args = args
		self.map_data = map_data
		self.borders = borders
		self.shifts = [1]

	def draw_tile(self, zoom, tx, ty, x_min, x_max, y_min, y_max,
				  tile_path, data_tile_path, borders_this_zoom,
				  also_save_transpa):
		args = self.args
		width = x_max - x_min
		height = y_max - y_min
		npx = width * height

		tile_dir = os.path.dirname(tile_path)
		if not os.path.isdir(tile_dir):
			os.makedirs(tile_dir)

		elev_data = load_elevation_tile(args["cacheDir"], zoom, tx, ty)

		# pixel grid, x-major like the C++ double loop
		xs = np.repeat(np.arange(x_min, x_max), height)
		ys = np.tile(np.arange(y_min, y_max), width)
		dx = tx + (xs.astype(F64) + 0.5) / float(TILE_RESOLUTION)
		dy = ty + (ys.astype(F64) + 0.5) / float(TILE_RESOLUTION)
		lat, lon = tile_pixel_to_latlon(dx, dy, zoom)

		corners = load_or_compute_corners(
			args["cacheDir"], zoom, tx, ty, x_min, x_max, y_min, y_max,
			self.map_data, lat, lon, self.shifts)

		valid = (corners >= 0).all(axis=1)

		# RGBA image, initialized like img.fill(qRgba(255,255,255,0))
		rgba = np.zeros((npx, 4), dtype=np.int64)
		rgba[:, 0:3] = 255

		data_bytes = None

		if valid.any():
			vc = corners[valid]
			c_lat = self.map_data.lat[vc]     # (n, 4) float32
			c_lon = self.map_data.lon[vc]
			c_vals = self.map_data.vals[vc]   # (n, 4, 28) float32
			vals = linear_interpolation(lat[valid], lon[valid], c_lat, c_lon, c_vals)

			elev = elevation_values(elev_data, xs[valid], ys[valid])
			MIN_ALTITUDE = F32(600.0)
			ADD_ELEVATION = 400.0
			elev_f = np.maximum((elev + ADD_ELEVATION).astype(F32), MIN_ALTITUDE)
			pression = nivellement_barometrique(
				np.maximum(elev_f, MIN_ALTITUDE), vals[:, 0:5])

			wind_angles = compute_wind_angles(vals)
			interpolated_val = interpolate_altitude(pression, vals[:, 5:10])
			interpolate_wind_val = interpolate_altitude(pression, vals[:, 11:16])
			fufu_val = vals[:, 10]
			interpolate_wind_angle = interpolate_altitude(pression, wind_angles)

			if data_tile_path:
				min_angle = F32(-2.0 * math.pi)
				max_angle = F32(2.0 * math.pi)
				angle_norm = ((interpolate_wind_angle - min_angle) /
							  (max_angle - min_angle)).astype(F32)
				cols = np.stack([
					quantize_byte(interpolated_val),
					quantize_byte(fufu_val),
					quantize_byte(interpolate_wind_val),
					quantize_byte(vals[:, 16]),
					quantize_byte(vals[:, 27]),
					quantize_byte(angle_norm),
				], axis=1)
				data_bytes = cols.astype(np.uint8).tobytes()

			if args["drawPngTiles"]:
				r, g, b = val_to_color(interpolated_val)
				sub = rgba[valid]
				sub[:, 0] = r
				sub[:, 1] = g
				sub[:, 2] = b
				sub[:, 3] = ALPHA_VALUE
				draw_fufu(sub, xs[valid] - x_min, ys[valid] - y_min, fufu_val)
				rgba[valid] = sub

		if args["drawPngTiles"]:
			draw_borders_using_histo(rgba, borders_this_zoom, tx, ty, width, height)
			# note: flights and decos are always empty in production
			# (takesOffFilename == "", DRAW_FLIGHTS disabled), not ported

			if args["backgroundTiles"]:
				if also_save_transpa:
					self._save_png(rgba, width, height,
								   tile_path.replace(".png", "_transpa.png"))
				self._blend_background(rgba, zoom, tx, ty, x_min, x_max,
									   y_min, y_max, width, height)

			self._save_png(rgba, width, height, tile_path)

		if data_tile_path and data_bytes is not None:
			tmp = data_tile_path + "_TMP"
			with open(tmp, "wb") as f:
				f.write(data_bytes)
			if os.path.exists(data_tile_path):
				os.remove(data_tile_path)
			os.rename(tmp, data_tile_path)
		elif data_tile_path:
			# no valid pixel at all: the C++ still creates the (empty) file
			tmp = data_tile_path + "_TMP"
			open(tmp, "wb").close()
			if os.path.exists(data_tile_path):
				os.remove(data_tile_path)
			os.rename(tmp, data_tile_path)

	def _blend_background(self, rgba, zoom, tx, ty, x_min, x_max, y_min, y_max,
						  width, height):
		args = self.args
		for btx in range(tx, tx + (x_max - 1) // TILE_RESOLUTION + 1):
			for bty in range(ty, ty + (y_max - 1) // TILE_RESOLUTION + 1):
				filename = "%s/%d/%d/%d.png" % (args["backgroundTiles"], zoom, btx, bty)
				if not os.path.isfile(filename):
					continue
				bg = np.asarray(Image.open(filename).convert("RGBA"), dtype=np.int64)
				# background pixel (x, y) lands on image pixel
				# (x - xMin + 256*(btx-tx), y - yMin + 256*(bty-ty))
				bx = np.arange(TILE_RESOLUTION)
				x_img = bx - x_min + TILE_RESOLUTION * (btx - tx)
				y_img = bx - y_min + TILE_RESOLUTION * (bty - ty)
				vx = (x_img >= 0) & (x_img < width)
				vy = (y_img >= 0) & (y_img < height)
				if not (vx.any() and vy.any()):
					continue
				xi = x_img[vx]
				yi = y_img[vy]
				# bg is (row=y, col=x, ch)
				bsel = bg[np.ix_(bx[vy], bx[vx])].astype(np.int64)
				gray = (bsel[:, :, 0] + bsel[:, :, 1] + bsel[:, :, 2]) // 3
				flat = rgba.reshape(width, height, 4)
				fg = flat[np.ix_(xi, yi)]  # (nx, ny, 4), x-major
				gray_t = gray.T  # to (x, y)
				for ch in range(3):
					# float r = (fg*ALPHA + (255-ALPHA)*gray) / 255.0f -- float32
					v = ((fg[:, :, ch] * ALPHA_VALUE +
						  (255 - ALPHA_VALUE) * gray_t).astype(F32) / F32(255.0)).astype(F32)
					# qRound(float), v >= 0
					fg[:, :, ch] = np.floor((v + F32(0.5)).astype(F64)).astype(np.int64)
				fg[:, :, 3] = 255
				flat[np.ix_(xi, yi)] = fg

	@staticmethod
	def _save_png(rgba, width, height, path):
		# rgba is x-major (width, height, 4); PIL expects (row=y, col=x)
		arr = rgba.reshape(width, height, 4).transpose(1, 0, 2)
		img = Image.fromarray(arr.astype(np.uint8), "RGBA")
		img.save(path)


# ============================================================================
# Legend images (main.cpp drawLegende)
# ============================================================================

def draw_legende(filename1, filename2, filename3):
	w, h = 256 + 1, 32 + 1

	if filename1:
		xs = np.repeat(np.arange(w), h)
		val = (xs.astype(F32) / F32(float(w - 1))).astype(F32)
		r, g, b = val_to_color(val)
		rgba = np.stack([r, g, b, np.full(w * h, ALPHA_VALUE, dtype=np.int64)], axis=1)
		TileRenderer._save_png(rgba, w, h, filename1)

	if filename2:
		r0, g0, b0 = val_to_color(np.array([1.0], dtype=F32))
		xs = np.repeat(np.arange(w), h)
		ys = np.tile(np.arange(h), w)
		val = (xs.astype(F32) / F32(float(w - 1))).astype(F32)
		rgba = np.zeros((w * h, 4), dtype=np.int64)
		rgba[:, 0] = r0[0]
		rgba[:, 1] = g0[0]
		rgba[:, 2] = b0[0]
		rgba[:, 3] = ALPHA_VALUE
		draw_fufu(rgba, xs, ys, val)
		TileRenderer._save_png(rgba, w, h, filename2)

	if filename3:
		w3 = h3 = 16 * 4 + 1
		xs = np.repeat(np.arange(w3), h3)
		ys = np.tile(np.arange(h3), w3)
		rgba = np.zeros((w3 * h3, 4), dtype=np.int64)
		rgba[:, 0:3] = 255
		draw_fufu(rgba, xs, ys, np.full(w3 * h3, F32(1.0)))
		TileRenderer._save_png(rgba, w3, h3, filename3)


# ============================================================================
# main
# ============================================================================

def set_progress(percent, progress_file):
	if not progress_file:
		return
	with open(progress_file, "w") as f:
		f.write(str(percent))


def load_skipped_tiles(filename):
	res = set()
	if not filename or not os.path.isfile(filename):
		return res
	with open(filename, "r") as f:
		for line in f:
			lst = line.split(" ")
			if len(lst) == 3:
				res.add((int(lst[0]), int(lst[1]), int(lst[2])))
	return res


def read_arguments(json_filename):
	with open(json_filename, "r") as f:
		raw = json.load(f)
	defaults = {
		"predictionFilename": "", "tilesDir": "", "drawPngTiles": True,
		"minZoom": -1, "maxZoom": -1, "cacheDir": "",
		"progressFilename": "", "bordersFilename": "",
		"minBordersZoom": -1, "maxBordersZoom": -1,
		"takesOffFilename": "", "backgroundTiles": "", "skippedTiles": "",
		"legendImg1": "", "legendImg2": "", "legendImg3": "",
		"generateTranspaVersion": True,
	}
	defaults.update(raw)
	return defaults


def main(argv):
	if len(argv) != 2:
		print("usage: tiler.py <tilerArguments.json>")
		return 1
	args = read_arguments(argv[1])

	map_data = MapData(args["predictionFilename"]) if args["predictionFilename"] else None
	borders = load_geojson(args["bordersFilename"])
	skipped = load_skipped_tiles(args["skippedTiles"])

	if args["legendImg1"] or args["legendImg2"] or args["legendImg3"]:
		draw_legende(args["legendImg1"], args["legendImg2"], args["legendImg3"])

	if not args["tilesDir"]:
		return 0

	renderer = TileRenderer(args, map_data, borders)

	# Vignette (zoom 5, fixed crop, no transpa version)
	zoom = 5
	borders_this_zoom = (convert_borders_coords(borders, zoom)
						 if args["minBordersZoom"] <= zoom <= args["maxBordersZoom"]
						 else [])
	renderer.shifts = [1]
	renderer.draw_tile(zoom, 15, 10,
					   114, TILE_RESOLUTION * 4 - 233,
					   127, TILE_RESOLUTION * 3 - 234,
					   args["tilesDir"] + "/vignette.png", "",
					   borders_this_zoom, False)

	# Tiles
	for zoom in range(args["minZoom"], args["maxZoom"] + 1):
		if args["maxZoom"] > args["minZoom"]:
			set_progress(25 + ((zoom - args["minZoom"]) * (70 - 25)) //
						 (args["maxZoom"] - args["minZoom"]),
						 args["progressFilename"])
		borders_this_zoom = (convert_borders_coords(borders, zoom)
							 if args["minBordersZoom"] <= zoom <= args["maxBordersZoom"]
							 else [])
		scale_factor = 2 ** (zoom - 5)
		renderer.shifts = [1]
		for tx in range(15 * scale_factor, (18 + 1) * scale_factor):
			for ty in range((9 - 1) * scale_factor, 13 * scale_factor):
				if (zoom, tx, ty) in skipped:
					continue
				tile_path = "%s/%d/%d/%d.png" % (args["tilesDir"], zoom, tx, ty)
				data_path = tile_path.replace(".png", ".data") if zoom == 7 else ""
				renderer.draw_tile(zoom, tx, ty, 0, TILE_RESOLUTION,
								   0, TILE_RESOLUTION, tile_path, data_path,
								   borders_this_zoom,
								   args["generateTranspaVersion"])
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
