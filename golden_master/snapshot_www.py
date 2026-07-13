# HTTP characterization snapshots of the Apache/PHP web layer (stage C3).
# Freezes the observable behavior of every endpoint (docs/web_inventory.md)
# against the golden-master data day, as the safety net for the FastAPI
# port (stage D2).
#
# Usage (inside the container, Apache running via scripts/start_server.sh,
# tiles for the GM day present in www/data/tiles/):
#   python golden_master/snapshot_www.py record   # write snapshots
#   python golden_master/snapshot_www.py check    # compare against stored
#
# Excluded on purpose:
#   - /apps/api/getAnalysisData.php -- mutates a tracked file
#     (banned.txt.php) on every mismatched request and depends on static
#     data files that are not in the repository; its honeypot behavior is
#     documented in docs/web_inventory.md and its fate is an open porting
#     decision.
#
# Note: sendMessage.php and generateApiKey.php currently return HTTP 500
# in any fresh clone because www/apps/mail_helper.php is not committed
# upstream (presumably kept private for SMTP credentials). The snapshots
# freeze that observable state on purpose.

import hashlib
import json
import os
import sys
import urllib.request
import urllib.error

# Default: the Apache/PHP original inside the legacy container. Override
# with SNAPSHOT_BASE to run the same characterization suite against the
# FastAPI port (stage D2), e.g. SNAPSHOT_BASE=http://127.0.0.1:8007
BASE = os.environ.get("SNAPSHOT_BASE", "http://localhost")
GM_DATE = "2026-07-09"
SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www_snapshots")

# (name, method, path, headers, post_data)
CASES = [
	("index_html", "GET", "/index.html", {}, None),
	("get_tile", "GET",
	 "/apps/api/get.php?tx=65&ty=45&x=128&y=128&zoom=7&date=%s" % GM_DATE, {}, None),
	("get_tile_elev", "GET",
	 "/apps/api/get.php?tx=65&ty=45&x=128&y=128&zoom=7&date=%s&elev=1" % GM_DATE, {}, None),
	("get_latlon", "GET",
	 "/apps/api/get.php?lat=45.9&lon=6.6&date=%s" % GM_DATE, {}, None),
	("get_latlon_spot", "GET",
	 "/apps/api/get.php?lat=45.9&lon=6.6&date=%s&spot=3323" % GM_DATE, {}, None),
	("get_missing_date", "GET",
	 "/apps/api/get.php?tx=65&ty=45&x=128&y=128&zoom=7&date=1999-01-01", {}, None),
	("get_bad_key", "GET", "/apps/api/get.php?key=zzz", {}, None),
	# Etappe E: hex-Schluessel gegen PostgreSQL; unbekannter Schluessel
	# antwortet deterministisch "unknown key" (vorher: 500 ohne DB).
	("get_key_unknown", "GET", "/apps/api/get.php?key=abc123", {}, None),
	("search_no_referer", "GET", "/apps/search.php?q=anne", {}, None),
	("search_with_referer", "GET", "/apps/search.php?q=anne",
	 {"Referer": "https://paraglidable.com/"}, None),
	("gtag_localhost", "GET", "/apps/gtag.php", {}, None),
	("send_message", "POST", "/apps/sendMessage.php", {},
	 b"name=Test&email=test%40example.org&text=snapshot"),
	# Etappe E: gueltige Anfragen liefern einen ZUFAELLIGEN Schluessel
	# (nicht snapshot-faehig); eingefroren wird die deterministische
	# Ablehnung einer ungueltigen E-Mail-Adresse.
	("generate_api_key", "GET",
	 "/apps/api/generateApiKey.php?email=kaputt"
	 "&lat_0=45.9&lon_0=6.6&name_0=Test&spotId_0=-1", {}, None),
]

# Bodies larger than this are stored as sha256 (static pages).
HASH_THRESHOLD = 4096


def fetch(method, path, headers, post_data):
	req = urllib.request.Request(BASE + path, data=post_data, method=method)
	for k, v in headers.items():
		req.add_header(k, v)
	try:
		with urllib.request.urlopen(req, timeout=30) as resp:
			return resp.status, resp.read()
	except urllib.error.HTTPError as e:
		return e.code, e.read()


def snapshot(name, method, path, headers, post_data):
	status, body = fetch(method, path, headers, post_data)
	rec = {"request": "%s %s" % (method, path), "status": status}
	if len(body) > HASH_THRESHOLD:
		rec["body_sha256"] = hashlib.sha256(body).hexdigest()
		rec["body_bytes"] = len(body)
	else:
		rec["body"] = body.decode("utf-8", "replace")
	return rec


def main():
	if len(sys.argv) != 2 or sys.argv[1] not in ("record", "check"):
		print("usage: snapshot_www.py record|check")
		sys.exit(2)
	mode = sys.argv[1]
	os.makedirs(SNAP_DIR, exist_ok=True)

	failures = 0
	for name, method, path, headers, post_data in CASES:
		rec = snapshot(name, method, path, headers, post_data)
		snap_file = os.path.join(SNAP_DIR, name + ".json")
		if mode == "record":
			with open(snap_file, "w") as f:
				json.dump(rec, f, indent=1, sort_keys=True)
				f.write("\n")
			print("[recorded] %s" % name)
		else:
			if not os.path.isfile(snap_file):
				print("[MISSING ] %s (no snapshot recorded)" % name)
				failures += 1
				continue
			with open(snap_file) as f:
				expected = json.load(f)
			if rec != expected:
				print("[DIFF    ] %s" % name)
				print("  expected: %s" % json.dumps(expected, sort_keys=True))
				print("  actual:   %s" % json.dumps(rec, sort_keys=True))
				failures += 1
			else:
				print("[OK      ] %s" % name)

	if mode == "check":
		print("RESULT:", "EQUIVALENT" if failures == 0 else "DEVIATION")
		sys.exit(1 if failures else 0)


if __name__ == "__main__":
	main()
