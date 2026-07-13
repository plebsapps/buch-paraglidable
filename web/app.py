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

import datetime
import hashlib
import json
import os
import random
import re
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.php_compat import (php_filter_int, php_filter_float, ctype_xdigit,
							php_round4, php_float_str, php_substr_byte,
							php_substr2_be, php_loose_eq_int,
							latlon_to_tile_coords, clean_search_q,
							php_json_pretty, php_htmlentities,
							php_validate_email)

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


@app.get("/mobile.html")
def mobile(request: Request):
	return templates.TemplateResponse(request=request, name="mobile.html")


@app.get("/mobileAndroid.html")
def mobile_android(request: Request):
	return templates.TemplateResponse(request=request, name="mobileAndroid.html")

# PHP's default response Content-Type under this Apache config.
PHP_CT = "text/html; charset=UTF-8"


def php_response(body, status=200, cors=False):
	headers = {"Access-Control-Allow-Origin": "*"} if cors else None
	return Response(content=body, status_code=status, media_type=PHP_CT,
					headers=headers)


# ============================================================================
# PostgreSQL (Etappe E): API-Schlüssel — Ersatz der MySQL-Tabellen des
# Originals (docs/web_inventory.md). Ohne PARAGLIDABLE_DB_URL oder ohne
# erreichbare DB bleiben die Endpunkte im eingefrorenen Zustand (HTTP 500),
# exakt wie vor Etappe E — der Umbau ist damit rückwärts harmlos.
# ============================================================================

def _db_connect():
	url = os.environ.get("PARAGLIDABLE_DB_URL")
	if not url:
		return None
	try:
		import psycopg2
		return psycopg2.connect(url)
	except Exception:
		return None


def generate_random_key():
	"""Port von generateRandomKey(): md5(rand()) erste 16 Hexzeichen,
	XOR mit fester Konstante, '%x'-Format (ohne führende Nullen)."""
	rnd_hex = hashlib.md5(str(random.randint(0, 2**31 - 1)).encode()).hexdigest()[:16]
	return "%x" % (int(rnd_hex, 16) ^ 0xddb5097051cd211d)


# ============================================================================
# /apps/api/get.php
# ============================================================================

def generate_xml(data):
	"""Port von generateXML(): identische Tabs/Zeilenumbrüche, Werte in
	PHP-Echo-Formatierung; wie das Original ohne XML-Escaping der Namen."""
	res = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
	res += "<paraglidable>\n"
	for date, data_day in data.items():
		res += "\t<day date=\"%s\">\n" % date
		for spot in data_day:
			res += ("\t\t<location name=\"%s\" lat=\"%s\" lon=\"%s\">\n"
					% (spot["name"], php_float_str(spot["lat"]),
					   php_float_str(spot["lon"])))
			res += "\t\t\t<forecast>\n"
			res += "\t\t\t\t<fly>%s</fly>\n" % php_float_str(spot["forecast"]["fly"])
			res += "\t\t\t\t<XC>%s</XC>\n" % php_float_str(spot["forecast"]["XC"])
			if "takeoff" in spot["forecast"]:
				res += ("\t\t\t\t<takeoff>%s</takeoff>\n"
						% php_float_str(spot["forecast"]["takeoff"]))
			res += "\t\t\t</forecast>\n"
			res += "\t\t</location>\n"
		res += "\t</day>\n"
	res += "</paraglidable>\n"
	return res


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
	# Etappe E (Migrate): dieser Leser bezieht die Spot-Prognose aus der
	# DB (jüngster Lauf, der den Tag trägt). Der Datei-Rückfall ist der
	# dokumentierte Rückweg von Expand and Contract und bedient zugleich
	# Tage vor Beginn der Spiegelung (z. B. den GM-Referenztag) sowie
	# DB-Ausfälle. Byte-gleichheit der Antwort: beide Seiten sind aus
	# demselben Text geparst (Nachweis: pipeline/verify_db_mirror.py).
	conn = _db_connect()
	if conn is not None:
		try:
			with conn.cursor() as cur:
				cur.execute(
					"SELECT flyability FROM spot_forecasts "
					"WHERE spot_id=%s AND valid_date=%s "
					"ORDER BY run_id DESC LIMIT 1", (spot_id, date))
				row = cur.fetchone()
			if row is not None:
				return row[0]
		except Exception:
			pass
		finally:
			conn.close()

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
		# Etappe E: Port des API-Zweigs von get.php gegen PostgreSQL
		# (Original: MySQL ApiKeys.latLonName, PHP-serialisierte Liste).
		# Ohne erreichbare DB bleibt der eingefrorene Zustand: HTTP 500,
		# leerer Body (wie die bdd.php-Fatalität des Originals).
		conn = _db_connect()
		if conn is None:
			return php_response("", status=500, cors=True)
		try:
			with conn.cursor() as cur:
				cur.execute("SELECT lat_lon_name FROM api_keys WHERE api_key=%s",
							(key,))
				rows = cur.fetchall()
		finally:
			conn.close()
		if len(rows) != 1:
			return php_response("unknown key", cors=True)
		spots_cfg = rows[0][0] or []

		data = {}
		for d in range(10):  # $nbDays = 10, ab heute
			date = (datetime.date.today()
					+ datetime.timedelta(days=d)).strftime("%Y-%m-%d")
			data_day = []
			for spot_cfg in spots_cfg:
				coords = latlon_to_tile_coords(spot_cfg["lat"], spot_cfg["lon"])
				vals = get_prediction(date, coords)
				if vals is None:
					continue  # PHP pusht nur bei $vals !== false
				forecast = {"fly": vals[0], "XC": vals[1]}
				spot_id = spot_cfg.get("spotId")
				if spot_id is not None and spot_id >= 0:
					spot_prediction = get_spot_prediction(date, spot_id)
					if spot_prediction is not None:
						forecast["takeoff"] = spot_prediction
				data_day.append({"lat": spot_cfg["lat"], "lon": spot_cfg["lon"],
								 "name": spot_cfg["name"], "forecast": forecast})
			data[date] = data_day

		fmt = q.get("format")
		wants_entities = bool(q.get("htmlentities"))
		if not fmt or fmt.lower() == "json":
			body = php_json_pretty(data)
			if wants_entities:
				return php_response(php_htmlentities(body), cors=True)
			return Response(content=body,
							media_type="application/json; charset=utf-8",
							headers={"Access-Control-Allow-Origin": "*"})
		body = generate_xml(data)
		if wants_entities:
			return php_response(php_htmlentities(body), cors=True)
		return Response(content=body, media_type="text/xml; charset=utf-8",
						headers={"Access-Control-Allow-Origin": "*"})

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
def generate_api_key(request: Request):
	# Etappe E: Port von generateApiKey.php gegen PostgreSQL. Bewusste
	# Abweichung vom Original (dokumentiert, Snapshot neu eingefroren):
	# Das Original mailte den Schlüssel und antwortete "1" — die
	# Mail-Infrastruktur existiert hier nicht (mail_helper.php upstream
	# privat, Kontaktweg in Etappe F entfernt). Diese Instanz liefert den
	# Schlüssel direkt im Antwort-Body; das Frontend zeigt ihn an.
	q = request.query_params
	email = php_validate_email(q.get("email"))
	if not email:
		return php_response("ERROR: invalide email")

	spots_cfg = []
	i = 0
	while ("lat_%d" % i) in q and ("lon_%d" % i) in q and ("name_%d" % i) in q:
		spots_cfg.append({
			"lat": php_filter_float(q.get("lat_%d" % i)),
			"lon": php_filter_float(q.get("lon_%d" % i)),
			"name": q.get("name_%d" % i),
			"spotId": php_filter_int(q.get("spotId_%d" % i)),
		})
		i += 1

	conn = _db_connect()
	if conn is None:
		# Eingefrorener Zustand ohne DB (wie vor Etappe E)
		return php_response("", status=500)
	try:
		api_key = generate_random_key()
		with conn:
			with conn.cursor() as cur:
				cur.execute(
					"INSERT INTO accounts (email) VALUES (%s) "
					"ON CONFLICT (email) DO NOTHING", (email,))
				cur.execute(
					"INSERT INTO api_keys (account_id, api_key, lat_lon_name) "
					"SELECT id, %s, %s FROM accounts WHERE email=%s "
					"ON CONFLICT (account_id) DO UPDATE SET "
					"api_key=EXCLUDED.api_key, lat_lon_name=EXCLUDED.lat_lon_name, "
					"created_at=now()",
					(api_key, json.dumps(spots_cfg), email))
	finally:
		conn.close()
	return php_response(api_key)


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
