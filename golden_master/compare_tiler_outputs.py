# Stage D1 pixel comparison: verify that the Python tiler (pipeline/tiler.py)
# reproduces the C++ Tiler output on IDENTICAL predictions.txt input.
#
# Unlike compare_golden_master.py (which samples PNGs and compares two full
# pipeline runs), this tool compares EVERY file below the two tile
# directories: all PNG tiles including the _transpa versions and
# vignette.png (pixel-wise), and all zoom-7 .data tiles (byte-wise).
#
# Tolerances (deliberately stricter than the golden-master tile tolerance
# of max-channel-diff 2 / 0.1% pixels per tile):
#   - .data tiles: byte-identical, no tolerance. The quantized values match
#     bit-for-bit because the whole value path is float32 in the same
#     operation order as the C++ code.
#   - PNG tiles: at most --max-channel-diff (default 1) per channel.
#     Measured cause of the residual differences: numpy's vectorized sin()
#     may differ from libm's sin() by 1 ulp; where the fufu blend
#     (1-mag)*c + mag*255 then lands exactly on an integer boundary, the
#     truncated channel value flips by 1. Zoom 7 measurement: 42 affected
#     pixels out of ~35 million (fraction 1.2e-6), always exactly 1 apart.
#
# Usage:
#   python compare_tiler_outputs.py <tiles_dir_a> <tiles_dir_b> \
#          [--max-channel-diff 1] [--max-diff-pixel-frac 0.0001]
#
# Exit code 0 = equivalent within tolerance, 1 = deviation.

import argparse
import os
import sys


def walk_files(d, suffix):
	out = []
	for root, _dirs, files in os.walk(d):
		for fn in files:
			if fn.endswith(suffix):
				out.append(os.path.relpath(os.path.join(root, fn), d))
	return sorted(out)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("dir_a")
	ap.add_argument("dir_b")
	ap.add_argument("--max-channel-diff", type=int, default=1)
	ap.add_argument("--max-diff-pixel-frac", type=float, default=0.0001)
	args = ap.parse_args()

	import numpy as np
	from PIL import Image

	rc = 0

	# --- PNG tiles, pixel-wise ---------------------------------------------
	pngs_a = walk_files(args.dir_a, ".png")
	pngs_b = walk_files(args.dir_b, ".png")
	if pngs_a != pngs_b:
		print("[DIFF] png sets differ: %d vs %d files" % (len(pngs_a), len(pngs_b)))
		rc = 1
	exact = 0
	within = 0
	diff_pixels = 0
	total_pixels = 0
	for rel in pngs_a:
		if rel not in pngs_b:
			continue
		a = np.asarray(Image.open(os.path.join(args.dir_a, rel)).convert("RGBA"), dtype=np.int16)
		b = np.asarray(Image.open(os.path.join(args.dir_b, rel)).convert("RGBA"), dtype=np.int16)
		if a.shape != b.shape:
			print("[DIFF] %s: shape %s vs %s" % (rel, a.shape, b.shape))
			rc = 1
			continue
		d = np.abs(a - b)
		total_pixels += a.shape[0] * a.shape[1]
		dmax = int(d.max())
		if dmax == 0:
			exact += 1
			continue
		npx = int((d.max(axis=2) > 0).sum())
		diff_pixels += npx
		frac = float(npx) / (a.shape[0] * a.shape[1])
		if dmax <= args.max_channel_diff and frac <= args.max_diff_pixel_frac:
			within += 1
		else:
			print("[DIFF] %s: max channel diff %d, %d pixels (%.5f%%)" %
				  (rel, dmax, npx, 100.0 * frac))
			rc = 1
	print("[%s] png tiles: %d exact, %d within +-%d (%d of %d pixels differ)" %
		  ("OK  " if rc == 0 else "    ", exact, within, args.max_channel_diff,
		   diff_pixels, total_pixels))

	# --- .data tiles, byte-exact -------------------------------------------
	data_a = walk_files(args.dir_a, ".data")
	data_b = walk_files(args.dir_b, ".data")
	if data_a != data_b:
		print("[DIFF] .data sets differ: %d vs %d files" % (len(data_a), len(data_b)))
		rc = 1
	data_ok = 0
	for rel in data_a:
		if rel not in data_b:
			continue
		with open(os.path.join(args.dir_a, rel), "rb") as fa, \
			 open(os.path.join(args.dir_b, rel), "rb") as fb:
			if fa.read() == fb.read():
				data_ok += 1
			else:
				print("[DIFF] .data tile %s not byte-identical" % rel)
				rc = 1
	print("[%s] data tiles: %d of %d byte-identical" %
		  ("OK  " if rc == 0 else "    ", data_ok, len(data_a)))

	print("RESULT:", "EQUIVALENT" if rc == 0 else "DEVIATION")
	sys.exit(rc)


if __name__ == "__main__":
	main()
