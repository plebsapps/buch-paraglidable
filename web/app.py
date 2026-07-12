# coding: utf-8
# FastAPI port of the Apache/PHP web layer (stage D2 of the modernization).
#
# Every endpoint reproduces the frozen observable behavior of the PHP
# original, verified against the 13 HTTP characterization snapshots
# (golden_master/snapshot_www.py, run with SNAPSHOT_BASE pointing here).
# PHP quirks are preserved on purpose -- see web/php_compat.py and the
# per-endpoint comments. Porting decisions (2026-07-11):
#   - search.php: ported 1:1
#   - gtag.php (Google Analytics of the original author): ported 1:1 in D2,
#     removed in stage F (2026-07-12) together with the frontend tracking
#     snippet -> the path now falls through to the static mount = 404.
#   - sendMessage.php / generateApiKey.php: the original answers HTTP 500
#     in every fresh clone (www/apps/mail_helper.php is not committed
#     upstream); that observable state is preserved until the API-key
#     database (stage E) exists. The contact form was removed in stage F.
#   - getAnalysisData.php (honeypot): deliberately NOT ported -> 404.
#
# Run:  uvicorn web.app:app  (see docker/web/ and docker-compose.yml)

import json
import os
import re
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.php_compat import (php_filter_int, php_filter_float, ctype_xdigit,
							php_round4, php_float_str, php_substr_byte,
							php_substr2_be, php_loose_eq_int,
							latlon_to_tile_coords, clean_search_q)

WWW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")

# Stage F2: the desktop page is rendered from Jinja2 templates (mechanical
# decomposition of the former static index.html). trim_blocks +
# keep_trailing_newline make the includes reproduce the original file
# byte for byte -- the proof that the decomposition changed nothing.
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR,
							trim_blocks=True, keep_trailing_newline=True)

app = FastAPI(title="Paraglidable web layer (D2 port)")


@app.get("/")
@app.get("/index.html")
def index(request: Request):
	return templates.TemplateResponse(request=request, name="index.html")

# PHP's default response Content-Type under this Apache config.
PHP_CT = "text/html; charset=UTF-8"


def php_response(body, status=200, cors=False):
	headers = {"Access-Control-Allow-Origin": "*"} if cors else None
	return Response(content=body, status_code=status, media_type=PHP_CT,
					headers=headers)


# ============================================================================
# /apps/api/get.php
# ============================================================================

def get_prediction(date, coords):
	"""Port of getPrediction() including the float nbVals arithmetic that
	governs short .data files (tiles with skipped pixels)."""
	filename = os.path.join(WWW_DIR, "data", "tiles", date, "256",
							str(coords["zoom"]), str(coords["tx"]),
							str(coords["ty"]) + ".data")
	try:
		with open(filename, "rb") as f:
			contents = f.read()
	except OSError:
		return None
	nb_vals = len(contents) / 65536.0  # PHP: strlen/(256*256), float!
	pos = nb_vals * (coords["x"] * 256 + coords["y"])
	vals = []
	v = 0
	while v < nb_vals:  # for ($v=0; $v<$nbVals; $v++)
		byte = php_substr_byte(contents, int(pos + v))
		vals.append(php_round4(byte / 255.0))
		v += 1
	return vals


def get_spot_prediction(date, spot_id):
	filename = os.path.join(WWW_DIR, "data", "tiles", date, "spots.json")
	try:
		with open(filename, "r") as f:
			ar = json.load(f)
	except OSError:
		return None
	for feature in ar.get("features", []):
		if php_loose_eq_int(feature["properties"]["id"], spot_id):
			return feature["properties"]["flyability"]
	return None


def get_elevation(coords):
	"""Port of getElevation(): uint16 big-endian (the PHP reads the signed
	int16 tiles unsigned -- preserved)."""
	filename = os.path.join(WWW_DIR, "data", "elevation",
							str(coords["zoom"]), str(coords["tx"]),
							str(coords["ty"]) + ".elev")
	try:
		with open(filename, "rb") as f:
			contents = f.read()
	except OSError:
		return None
	return php_substr2_be(contents, 2 * (coords["x"] * 256 + coords["y"]))


@app.get("/apps/api/get.php")
def api_get(request: Request):
	q = request.query_params

	# if ($_GET['key'] && !ctype_xdigit($_GET['key'])) die("unknown key");
	key = q.get("key")
	if key and not ctype_xdigit(key):
		return php_response("unknown key", cors=True)

	tx = php_filter_int(q.get("tx"))
	ty = php_filter_int(q.get("ty"))
	x = php_filter_int(q.get("x"))
	y = php_filter_int(q.get("y"))
	zoom = php_filter_int(q.get("zoom"))
	elev = php_filter_int(q.get("elev"))
	spot = php_filter_int(q.get("spot"))
	lat = php_filter_float(q.get("lat"))
	lon = php_filter_float(q.get("lon"))
	check_date = bool(re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", q.get("date") or ""))

	if ("key" not in q
			and (tx is None or ty is None or x is None or y is None
				 or zoom is None or not check_date)
			and (lat is None or lon is None or not check_date)):
		return php_response("", cors=True)

	if "key" in q:
		# Frozen state (see snapshot get_key_no_db): the PHP DB layer
		# (mysqli/MySQL) does not exist in any fresh clone, the include of
		# bdd.php dies fatally -> HTTP 500, empty body. Real API-key
		# handling arrives with PostgreSQL in stage E.
		return php_response("", status=500, cors=True)

	# if ($_GET['lat'] || $_GET['lon']) -- PHP truthiness: 0.0 is falsy
	if lat or lon:
		coords = latlon_to_tile_coords(lat or 0.0, lon or 0.0)
	else:
		coords = {"tx": tx, "ty": ty, "x": x, "y": y, "zoom": zoom}

	date = q.get("date")
	vals = get_prediction(date, coords)

	elev_val = None
	if elev == 1:
		elev_val = get_elevation(coords)

	if spot is not None and spot >= 0 and vals is not None:
		spot_prediction = get_spot_prediction(date, spot)
		if spot_prediction is not None:
			vals.append(spot_prediction)

	if vals is None:
		return php_response("", cors=True)
	body = ",".join(php_float_str(v) for v in vals)
	if elev_val is not None:
		body += ";%d" % elev_val
	return php_response(body, cors=True)


# ============================================================================
# /apps/search.php
# ============================================================================

ALLOWED_REFERERS = ("paraglidable.com", "paraglidable.net",
					"v1.paraglidable.com", "v1.paraglidable.net")


@app.get("/apps/search.php")
def search(request: Request):
	referer = request.headers.get("referer", "")
	allowed = any(referer.startswith("https://" + r) for r in ALLOWED_REFERERS)
	body = b""
	if allowed:
		cleaned = clean_search_q(request.query_params.get("q") or "")
		# Proxy to the static spot search index like the original; in this
		# deployment nothing listens there, so the answer stays empty like
		# the frozen snapshot (error_reporting(0) in the PHP).
		try:
			with urllib.request.urlopen(
					"http://localhost:8001/q/%s.js" % cleaned, timeout=5) as resp:
				body = resp.read()
		except Exception:
			body = b""
	return php_response(body)


# ============================================================================
# /apps/sendMessage.php and /apps/api/generateApiKey.php
# ============================================================================

@app.api_route("/apps/sendMessage.php", methods=["GET", "POST"])
def send_message():
	# require of the upstream-private mail_helper.php dies fatally.
	return php_response("", status=500)


@app.api_route("/apps/api/generateApiKey.php", methods=["GET", "POST"])
def generate_api_key():
	# Same frozen 500: mail helper and MySQL are absent in every clone.
	return php_response("", status=500)


# ============================================================================
# Static files (1:1 like Apache), .php sources must never be served
# ============================================================================

class PhpAwareStaticFiles(StaticFiles):
	async def get_response(self, path, scope):
		if path.endswith(".php"):
			# Unported endpoints (e.g. the getAnalysisData.php honeypot,
			# deliberately not ported) and raw .php sources: 404.
			return Response(content="", status_code=404, media_type=PHP_CT)
		return await super().get_response(path, scope)


app.mount("/", PhpAwareStaticFiles(directory=WWW_DIR, html=True), name="www")
