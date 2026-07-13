# coding: utf-8
# Stage D3: replaces scripts/cron_tasks (host cron on the original server)
# with an APScheduler worker running inside the frozen pipeline image
# (Python 3.6) as its own Compose service. See docker/worker/ and
# docker-compose.yml. Logging goes to container stdout.
#
# Ported jobs and their original cadence (scripts/cron_tasks/crontab.txt):
#   forecast  */30 min   update_forecasts.sh -> python -m pipeline run
#   commit    */21 min   set_current_commit.py -> www/data/commit.txt
#   clean     02:00      clean.py (old meteo files, old tile days)
# Deliberately NOT ported:
#   check_server.py       monitors paraglidable.com and mails the original
#                         author; monitoring of this instance is an
#                         operator concern (nginx/uptime), no mail infra
#   reboot.sh             container restart policy covers it; the search
#                         index container (osmnames on :8001) never existed
#                         on this instance (search.php stays frozen-empty)
#   renew_certificates.sh certbot runs on the host (see docs/deployment.md)
#
# Every job can also be run once from the CLI (inside the container):
#   python3 pipeline/scheduler.py forecast|commit|clean

from __future__ import print_function

import argparse
import datetime
import os
import shutil
import subprocess
import sys

ROOT = "/workspaces/Paraglidable"

# Etappe E: der Scheduler läuft als "python3 pipeline/scheduler.py" --
# sys.path[0] ist dann pipeline/, nicht das Repo-Root, und
# "from pipeline import db" schlägt fehl (Fund im ersten Produktionslauf
# mit Spiegel, 2026-07-13: "No module named 'pipeline'").
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

NB_DAYS = 10  # forecast horizon, same constant as forecast.py/clean.py

# Paths of the Docker environment (forecast.py in_docker branch + clean.py)
TILES_DIR = os.path.join(ROOT, "www", "data", "tiles")
COMMIT_TXT = os.path.join(ROOT, "www", "data", "commit.txt")
LAST_FORECAST_TIME_DIR = "/tmp/lastForecastTime"
DOWNLOADED_FORECASTS_DIR = "/tmp/forecasts"
API_REFERERS = "/tmp/apiCalls.txt"


def log(msg):
	print("[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
	sys.stdout.flush()


# ============================================================================
# job: forecast (update_forecasts.sh)
# ============================================================================

def job_forecast():
	# Fresh process per run (cron semantics): TF memory is released after
	# each run, which matters on the 1.8 GB server. forecast.py itself
	# skips cycles it has already processed (/tmp/lastForecastTime).
	log("forecast: starting 'python -m pipeline run'")
	ret = subprocess.call(["python3", "-m", "pipeline", "run"], cwd=ROOT)
	log("forecast: finished with exit code %d" % ret)
	# Etappe E: nach Abstürzen liegengebliebene Lauf-Zeilen schließen
	# (No-op ohne PARAGLIDABLE_DB_URL; der reguläre Abschluss passiert
	# im Lauf selbst, neural_network/forecast.py main()).
	try:
		from pipeline import db as pipeline_db
		pipeline_db.close_dangling(ret)
		# Vergleichsjob (Expand and Contract): Nachweis, dass Datei und
		# DB-Spiegel denselben Inhalt tragen — Ergebnis nur ins Log,
		# der Betrieb hängt weiter allein an den Dateien.
		if ret == 0 and pipeline_db.enabled():
			from pipeline import verify_db_mirror
			log("forecast: Vergleich Datei<->DB %s" % (
				"EQUIVALENT" if verify_db_mirror.verify_run() else "DIFFERENT"))
	except Exception as e:
		log("forecast: DB-Laufabschluss fehlgeschlagen: %s" % e)


# ============================================================================
# job: commit (set_current_commit.py) — pure-Python HEAD lookup, no git
# binary needed (the repo is a host mount; git would demand safe.directory)
# ============================================================================

def _read_git_head(git_dir):
	with open(os.path.join(git_dir, "HEAD")) as f:
		head = f.read().strip()
	if not head.startswith("ref: "):
		return head  # detached HEAD
	ref = head[len("ref: "):]
	ref_file = os.path.join(git_dir, ref)
	if os.path.exists(ref_file):
		with open(ref_file) as f:
			return f.read().strip()
	packed = os.path.join(git_dir, "packed-refs")
	if os.path.exists(packed):
		with open(packed) as f:
			for line in f:
				if line.strip().endswith(" " + ref) or line.strip().endswith("\t" + ref):
					return line.split()[0]
	raise RuntimeError("unresolvable ref: %s" % ref)


def job_commit():
	commit = _read_git_head(os.path.join(ROOT, ".git"))
	with open(COMMIT_TXT, "w") as fout:
		fout.write(commit)
	log("commit: wrote %s to %s" % (commit[:8], COMMIT_TXT))


# ============================================================================
# job: clean (clean.py) — same logic, Docker paths
# ============================================================================

def _remove_dir(path):
	try:
		shutil.rmtree(path)
		log("clean: removed dir  %s" % path)
	except OSError:
		pass


def _remove_file(path):
	try:
		os.remove(path)
		log("clean: removed file %s" % path)
	except OSError:
		pass


def job_clean():
	log("clean: starting")
	_remove_file(API_REFERERS)

	# all past days: forecast-time markers and downloaded meteo files
	for delta_days in range(1, 100):
		strday = (datetime.datetime.now() + datetime.timedelta(days=-delta_days)).strftime("%Y-%m-%d")
		_remove_file(os.path.join(LAST_FORECAST_TIME_DIR, strday))
		for h in [6, 12, 18]:
			_remove_file(os.path.join(DOWNLOADED_FORECASTS_DIR, strday + ("-%02d" % h)))

	# far past days: tile directories beyond the forecast horizon
	for delta_days in range(NB_DAYS + 1, 100):
		strday = (datetime.datetime.now() + datetime.timedelta(days=-delta_days)).strftime("%Y-%m-%d")
		_remove_dir(os.path.join(TILES_DIR, strday))

	# Etappe E: alte DB-Läufe entfernen (No-op ohne PARAGLIDABLE_DB_URL);
	# Kinder-Zeilen (Zellen/Spots/Kachel-Metadaten) fallen per CASCADE mit
	try:
		from pipeline import db as pipeline_db
		if pipeline_db.enabled():
			pipeline_db.prune_runs()
			log("clean: DB-Läufe auf die letzten %d begrenzt" % pipeline_db.KEEP_RUNS)
	except Exception as e:
		log("clean: DB-Aufräumen fehlgeschlagen: %s" % e)
	log("clean: finished")


# ============================================================================
# main: one-shot CLI or scheduler loop
# ============================================================================

JOBS = {"forecast": job_forecast, "commit": job_commit, "clean": job_clean}


def main():
	parser = argparse.ArgumentParser(
		description="Paraglidable worker: APScheduler replacement for scripts/cron_tasks")
	parser.add_argument("job", nargs="?", choices=sorted(JOBS),
						help="run a single job once and exit (default: scheduler loop)")
	args = parser.parse_args()

	if args.job:
		JOBS[args.job]()
		return

	from apscheduler.schedulers.blocking import BlockingScheduler

	scheduler = BlockingScheduler(timezone="Europe/Zurich")
	# Original cadences from crontab.txt; max_instances=1 serializes the
	# long forecast run, coalesce collapses missed triggers into one.
	scheduler.add_job(job_forecast, "cron", minute="*/30", id="forecast",
					  max_instances=1, coalesce=True, misfire_grace_time=300)
	scheduler.add_job(job_commit, "cron", minute="*/21", id="commit",
					  coalesce=True, misfire_grace_time=300)
	scheduler.add_job(job_clean, "cron", hour=2, minute=0, id="clean",
					  coalesce=True, misfire_grace_time=3600)

	log("worker: scheduler starting (forecast */30min, commit */21min, clean 02:00 %s)"
		% "Europe/Zurich")
	job_commit()  # publish the running commit immediately at startup
	scheduler.start()


if __name__ == "__main__":
	main()
