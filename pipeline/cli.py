# coding: utf-8
# CLI for the forecast pipeline (stage C2 of the modernization).
#
# Exposes the steps of neural_network/forecast.py -- download / forecast /
# tile / publish -- as individually runnable commands, plus `run`, which
# behaves exactly like the legacy `python3 forecast.py` (minus the
# already-running guard, which stays in the legacy entry point).
#
# The steps communicate through files only:
#   download  ->  GRIB files       (--grib-dir, default /tmp/forecasts)
#   forecast  ->  predictions.txt  (--predictions) and
#                 <tiles-dir>/<date>/spots.json
#   tile      ->  tilerArguments.json (--tiler-args) and
#                 <tiles-dir>/<date>/... PNG/data tiles
#   publish   ->  freshness stamp (--last-forecast-time-dir) and progress.txt
#
# Usage (inside the container, from the repository root):
#   python -m pipeline run
#   python -m pipeline download --cycle 2026070906 --day 0
#   python -m pipeline forecast --date 2026-07-09 --meteo-files A B C
#   python -m pipeline tile     --date 2026-07-09
#   python -m pipeline publish  --cycle 2026070906 --date 2026-07-09

import argparse
import datetime
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NN_DIR = os.path.join(ROOT, "neural_network")


def _make_forecast(args):
	"""Build the Forecast object with the same defaults as the legacy
	entry point, then apply the path overrides from the command line.

	forecast.py resolves its model directory and BinObj caches relative
	to the neural_network directory, hence chdir + sys.path (same as
	golden_master/run_golden_master.py)."""
	os.chdir(NN_DIR)
	sys.path.insert(0, NN_DIR)
	import forecast as forecast_mod
	from inc.model import ProblemFormulation

	problem_formulation = ProblemFormulation.CLASSIFICATION
	model_dir = "./bin/models/%s_1.0.0" % str(problem_formulation).split(".")[-1]
	f = forecast_mod.Forecast(model_dir, problem_formulation)

	if getattr(args, "grib_dir", None):
		f.downloaded_forecasts_dir = args.grib_dir
		f.destination_forecast_file = os.path.join(args.grib_dir, "%s")
		os.makedirs(args.grib_dir, exist_ok=True)
	if getattr(args, "predictions", None):
		f.prediction_filename_for_tiler = args.predictions
	if getattr(args, "tiler_args", None):
		f.tiler_arguments_filename = args.tiler_args
	if getattr(args, "tiles_dir", None):
		f.tiles_dir = args.tiles_dir
	if getattr(args, "last_forecast_time_dir", None):
		f.last_forecast_time_file_dir = args.last_forecast_time_dir
		os.makedirs(args.last_forecast_time_dir, exist_ok=True)
	return f


def _parse_cycle(cycle):
	"""YYYYMMDDHH -> (datetime of the day, forecast hour)."""
	if len(cycle) != 10 or not cycle.isdigit():
		sys.exit("--cycle must be YYYYMMDDHH, e.g. 2026070906")
	return (datetime.datetime(int(cycle[0:4]), int(cycle[4:6]), int(cycle[6:8])),
	        int(cycle[8:10]))


def _parse_date(strdate):
	try:
		return datetime.datetime.strptime(strdate, "%Y-%m-%d")
	except ValueError:
		sys.exit("--date must be YYYY-MM-DD, e.g. 2026-07-09")


def cmd_download(args):
	f = _make_forecast(args)
	cycle_dt, cycle_hour = _parse_cycle(args.cycle)
	day_datetime = cycle_dt + datetime.timedelta(days=args.day)
	meteo_files = f.step_download(args.cycle, cycle_hour, args.day, day_datetime)
	if meteo_files is None:
		sys.exit("meteo files missing after download, day skipped")
	for mf in meteo_files:
		print(mf)


def cmd_forecast(args):
	f = _make_forecast(args)
	day_datetime = _parse_date(args.date)
	if args.meteo_files:
		# Same protection as the forced_meteo_files seam in step_download:
		# work on copies so the given files (e.g. the frozen golden-master
		# input) are never deleted by the post-forecast cleanup.
		if len(args.meteo_files) != 3:
			sys.exit("--meteo-files needs exactly 3 paths (06, 12, 18)")
		meteo_files = ["/tmp/forced_meteo_06", "/tmp/forced_meteo_12", "/tmp/forced_meteo_18"]
		for src, dst in zip(args.meteo_files, meteo_files):
			shutil.copyfile(src, dst)
	else:
		# Same file-list recreation as in step_download.
		meteo_files = [f.destination_forecast_file %
		               (day_datetime + datetime.timedelta(hours=h)).strftime("%Y-%m-%d-%H")
		               for h in [6, 12, 18]]
	os.makedirs(os.path.join(f.tiles_dir, args.date), exist_ok=True)
	f.step_forecast(meteo_files, args.date)


def cmd_tile(args):
	f = _make_forecast(args)
	_parse_date(args.date)
	tiles_dir_this_day = f.tiles_dir + "/" + args.date
	os.makedirs(tiles_dir_this_day, exist_ok=True)
	f.step_tile(tiles_dir_this_day)


def cmd_publish(args):
	f = _make_forecast(args)
	day_datetime = _parse_date(args.date)
	_parse_cycle(args.cycle)
	os.makedirs(os.path.join(f.tiles_dir, args.date), exist_ok=True)
	f.step_publish(day_datetime, args.cycle, args.date)


def cmd_run(args):
	f = _make_forecast(args)
	f.main()


def _add_path_opts(parser, *names):
	opts = {
		"grib_dir": ("--grib-dir", "directory for downloaded GRIB files"),
		"predictions": ("--predictions", "path of predictions.txt"),
		"tiler_args": ("--tiler-args", "path of tilerArguments.json"),
		"tiles_dir": ("--tiles-dir", "root directory of the tiles"),
		"last_forecast_time_dir": ("--last-forecast-time-dir",
		                           "directory of the freshness stamps"),
	}
	for name in names:
		flag, help_text = opts[name]
		parser.add_argument(flag, dest=name, default=None,
		                    help=help_text + " (default: legacy path)")


def build_parser():
	parser = argparse.ArgumentParser(
		prog="python -m pipeline",
		description="Forecast pipeline as individually runnable steps (stage C2).")
	# Python 3.6 in the frozen container: add_subparsers() has no
	# `required` kwarg yet.
	sub = parser.add_subparsers(dest="command")
	sub.required = True

	p = sub.add_parser("run", help="full run, behaves like the legacy forecast.py")
	_add_path_opts(p, "grib_dir", "predictions", "tiler_args", "tiles_dir",
	               "last_forecast_time_dir")
	p.set_defaults(func=cmd_run)

	p = sub.add_parser("download", help="fetch the GRIB files for one valid day")
	p.add_argument("--cycle", required=True, help="GFS cycle YYYYMMDDHH")
	p.add_argument("--day", type=int, default=0,
	               help="day offset from the cycle date (default 0)")
	_add_path_opts(p, "grib_dir")
	p.set_defaults(func=cmd_download)

	p = sub.add_parser("forecast",
	                   help="compute predictions.txt and spots.json for one day")
	p.add_argument("--date", required=True, help="valid day YYYY-MM-DD")
	p.add_argument("--meteo-files", nargs="+", default=None,
	               help="explicit GRIB files 06/12/18 (copied, originals kept); "
	                    "default: files from the download step")
	_add_path_opts(p, "grib_dir", "predictions", "tiles_dir")
	p.set_defaults(func=cmd_forecast)

	p = sub.add_parser("tile", help="render the tiles for one day")
	p.add_argument("--date", required=True, help="valid day YYYY-MM-DD")
	_add_path_opts(p, "predictions", "tiler_args", "tiles_dir")
	p.set_defaults(func=cmd_tile)

	p = sub.add_parser("publish",
	                   help="mark one day as up-to-date (freshness stamp, progress)")
	p.add_argument("--date", required=True, help="valid day YYYY-MM-DD")
	p.add_argument("--cycle", required=True, help="GFS cycle YYYYMMDDHH")
	_add_path_opts(p, "tiles_dir", "last_forecast_time_dir")
	p.set_defaults(func=cmd_publish)

	return parser


def main(argv=None):
	args = build_parser().parse_args(argv)
	args.func(args)


if __name__ == "__main__":
	main()
