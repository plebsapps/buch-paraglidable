# Golden-master runner: reproducible forecast pipeline run on frozen GFS input.
#
# Runs the unmodified Forecast pipeline (neural_network/forecast.py) on the
# three archived GRIB files in golden_master/input/ via the existing
# forced_meteo_files seam -- no network access, no live cycle detection.
# All outputs (predictions.txt, tilerArguments.json, spots.json, tiles) go
# into a per-run directory so that independent runs can be compared.
#
# Usage (inside the container):
#   python /workspaces/Paraglidable/golden_master/run_golden_master.py <run_dir>
#
# Part of stage A3 of the modernization (see golden_master/README.md).

import os
import sys

ROOT = "/workspaces/Paraglidable"
NN_DIR = os.path.join(ROOT, "neural_network")
GM_INPUT = os.path.join(ROOT, "golden_master", "input")
GM_CYCLE = "2026070906"  # frozen GFS cycle, see golden_master/README.md
GM_METEO_FILES = [os.path.join(GM_INPUT, f) for f in
                  ["2026-07-09-06", "2026-07-09-12", "2026-07-09-18"]]

# Determinism knobs -- must be set before TensorFlow is imported.
os.environ["TF_DETERMINISTIC_OPS"] = "1"
os.environ["TF_CUDNN_DETERMINISTIC"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # CPU only


def main():
	if len(sys.argv) != 2:
		print("usage: run_golden_master.py <run_dir>")
		sys.exit(2)
	run_dir = os.path.abspath(sys.argv[1])
	os.makedirs(run_dir, exist_ok=True)

	for mf in GM_METEO_FILES:
		if not os.path.isfile(mf) or os.path.getsize(mf) < 5000:
			print("ERROR: frozen input missing or too small:", mf)
			sys.exit(1)

	# forecast.py resolves its model directory and BinObj caches relative
	# to the neural_network directory.
	os.chdir(NN_DIR)
	sys.path.insert(0, NN_DIR)

	import random
	import numpy as np
	random.seed(0)
	np.random.seed(0)

	import tensorflow as tf
	try:
		tf.config.threading.set_intra_op_parallelism_threads(1)
		tf.config.threading.set_inter_op_parallelism_threads(1)
	except Exception as e:  # older TF2 builds may differ; record, don't die
		print("[WARNING] could not pin TF threads:", e)
	try:
		tf.random.set_seed(0)
	except Exception as e:
		print("[WARNING] could not set TF seed:", e)

	import forecast as forecast_mod
	from inc.model import ProblemFormulation

	# No network: the cycle is fixed to the frozen input.
	forecast_mod.Forecast.get_last_forecast_times = staticmethod(lambda grid: [GM_CYCLE])

	problem_formulation = ProblemFormulation.CLASSIFICATION
	model_dir = "./bin/models/%s_1.0.0" % str(problem_formulation).split(".")[-1]

	f = forecast_mod.Forecast(model_dir, problem_formulation)
	f.forced_meteo_files = GM_METEO_FILES
	f.nb_days = 1  # exactly one valid day: 2026-07-09
	# Per-run outputs and per-run freshness cache (never skip computation).
	f.last_forecast_time_file_dir = os.path.join(run_dir, "lastForecastTime")
	f.prediction_filename_for_tiler = os.path.join(run_dir, "predictions.txt")
	f.tiler_arguments_filename = os.path.join(run_dir, "tilerArguments.json")
	f.tiles_dir = os.path.join(run_dir, "tiles")
	os.makedirs(f.last_forecast_time_file_dir, exist_ok=True)
	os.makedirs(f.tiles_dir, exist_ok=True)

	f.main()

	print("golden-master run complete:", run_dir)


if __name__ == "__main__":
	main()
