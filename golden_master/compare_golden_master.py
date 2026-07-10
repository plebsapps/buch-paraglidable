# Golden-master comparison: verify that two pipeline runs are equivalent
# within defined tolerances. Exit code 0 = equivalent, 1 = deviation.
#
# Three-tier comparison (see golden_master/README.md):
#   1. predictions.txt  -- numeric compare, token by token (primary reference)
#   2. tiles/           -- pixel compare on a deterministic sample of PNGs
#   3. spots.json       -- structure must match exactly, numbers with tolerance
#
# The predictions.txt format is an undocumented ad-hoc text format (its
# specification is produced later, in stage C1). Until then the comparison
# is format-agnostic: non-numeric tokens must match exactly, numeric tokens
# must match within tolerance.
#
# Usage:
#   python compare_golden_master.py <run_dir_a> <run_dir_b> \
#          [--rtol 1e-5] [--atol 1e-7] \
#          [--max-channel-diff 2] [--max-diff-pixel-frac 0.001] \
#          [--tile-sample 50]

import argparse
import json
import os
import re
import sys

NUM_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def fail(msg):
	print("[DIFF] " + msg)
	return 1


def compare_text_numeric(path_a, path_b, rtol, atol):
	"""Token-wise compare: numbers with tolerance, everything else exactly."""
	errors = 0
	max_rel = 0.0
	with open(path_a, "r") as fa, open(path_b, "r") as fb:
		lines_a = fa.readlines()
		lines_b = fb.readlines()
	if len(lines_a) != len(lines_b):
		return fail("%s: line count differs: %d vs %d" %
					(os.path.basename(path_a), len(lines_a), len(lines_b))), 0.0
	for i, (la, lb) in enumerate(zip(lines_a, lines_b)):
		if la == lb:
			continue
		toks_a = NUM_RE.findall(la)
		toks_b = NUM_RE.findall(lb)
		skel_a = NUM_RE.sub("#", la)
		skel_b = NUM_RE.sub("#", lb)
		if skel_a != skel_b or len(toks_a) != len(toks_b):
			errors += fail("%s line %d: structure differs" %
						   (os.path.basename(path_a), i + 1))
			if errors > 20:
				break
			continue
		for ta, tb in zip(toks_a, toks_b):
			va, vb = float(ta), float(tb)
			if abs(va - vb) > atol + rtol * abs(vb):
				errors += fail("%s line %d: %s vs %s exceeds tolerance" %
							   (os.path.basename(path_a), i + 1, ta, tb))
				break
			denom = max(abs(va), abs(vb), 1e-30)
			max_rel = max(max_rel, abs(va - vb) / denom)
		if errors > 20:
			break
	return (1 if errors else 0), max_rel


def compare_json(path_a, path_b, rtol, atol):
	with open(path_a) as fa, open(path_b) as fb:
		ja, jb = json.load(fa), json.load(fb)
	diffs = []

	def rec(a, b, path):
		if len(diffs) > 20:
			return
		if type(a) is not type(b):
			diffs.append("%s: type differs" % path)
		elif isinstance(a, dict):
			if sorted(a.keys()) != sorted(b.keys()):
				diffs.append("%s: keys differ" % path)
			else:
				for k in a:
					rec(a[k], b[k], path + "/" + str(k))
		elif isinstance(a, list):
			if len(a) != len(b):
				diffs.append("%s: list length differs" % path)
			else:
				for i, (xa, xb) in enumerate(zip(a, b)):
					rec(xa, xb, path + "[%d]" % i)
		elif isinstance(a, float) or isinstance(a, int):
			if abs(a - b) > atol + rtol * abs(b):
				diffs.append("%s: %s vs %s" % (path, a, b))
		elif a != b:
			diffs.append("%s: %r vs %r" % (path, a, b))

	rec(ja, jb, os.path.basename(path_a))
	for d in diffs:
		fail(d)
	return 1 if diffs else 0


def compare_tiles(dir_a, dir_b, sample, max_channel_diff, max_diff_frac):
	from PIL import Image
	import numpy as np

	def png_set(d):
		out = []
		for root, _dirs, files in os.walk(d):
			for fn in files:
				if fn.endswith(".png"):
					out.append(os.path.relpath(os.path.join(root, fn), d))
		return sorted(out)

	set_a, set_b = png_set(dir_a), png_set(dir_b)
	if set_a != set_b:
		only_a = set(set_a) - set(set_b)
		only_b = set(set_b) - set(set_a)
		return fail("tile sets differ (only in a: %d, only in b: %d)" %
					(len(only_a), len(only_b)))
	if not set_a:
		return fail("no tiles found in %s" % dir_a)

	# Deterministic sample: every k-th tile of the sorted list.
	step = max(1, len(set_a) // sample)
	checked = 0
	errors = 0
	for rel in set_a[::step]:
		a = np.asarray(Image.open(os.path.join(dir_a, rel)).convert("RGBA"), dtype=np.int16)
		b = np.asarray(Image.open(os.path.join(dir_b, rel)).convert("RGBA"), dtype=np.int16)
		if a.shape != b.shape:
			errors += fail("tile %s: shape differs" % rel)
			continue
		diff = np.abs(a - b)
		if diff.max() > max_channel_diff:
			frac = float((diff.max(axis=2) > max_channel_diff).mean())
			if frac > max_diff_frac:
				errors += fail("tile %s: max channel diff %d, %.4f%% pixels differ" %
							   (rel, int(diff.max()), 100.0 * frac))
		checked += 1
		if errors > 20:
			break
	print("[OK   ] tiles: %d of %d sampled and compared" % (checked, len(set_a)))
	return 1 if errors else 0


def find_spots_json(run_dir):
	tiles = os.path.join(run_dir, "tiles")
	for root, _dirs, files in os.walk(tiles):
		if "spots.json" in files:
			return os.path.join(root, "spots.json")
	return None


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("run_a")
	ap.add_argument("run_b")
	ap.add_argument("--rtol", type=float, default=1e-5)
	ap.add_argument("--atol", type=float, default=1e-7)
	ap.add_argument("--max-channel-diff", type=int, default=2)
	ap.add_argument("--max-diff-pixel-frac", type=float, default=0.001)
	ap.add_argument("--tile-sample", type=int, default=50)
	args = ap.parse_args()

	rc = 0

	# 1. Primary: raw predictions
	pa = os.path.join(args.run_a, "predictions.txt")
	pb = os.path.join(args.run_b, "predictions.txt")
	r, max_rel = compare_text_numeric(pa, pb, args.rtol, args.atol)
	rc |= r
	if not r:
		print("[OK   ] predictions.txt within tolerance (max relative deviation: %.3e)" % max_rel)

	# 2. Secondary: rendered tiles
	rc |= compare_tiles(os.path.join(args.run_a, "tiles"),
						os.path.join(args.run_b, "tiles"),
						args.tile_sample, args.max_channel_diff,
						args.max_diff_pixel_frac)

	# 3. Spots forecast as served to the website
	sa, sb = find_spots_json(args.run_a), find_spots_json(args.run_b)
	if sa is None or sb is None:
		rc |= fail("spots.json missing in one of the runs")
	else:
		r = compare_json(sa, sb, args.rtol, args.atol)
		rc |= r
		if not r:
			print("[OK   ] spots.json equivalent")

	print("RESULT:", "EQUIVALENT" if rc == 0 else "DEVIATION")
	sys.exit(rc)


if __name__ == "__main__":
	main()
