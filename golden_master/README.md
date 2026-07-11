# Golden Master

Frozen reference for behavior-preserving modernization (see NOTICE).
The data files in this directory are NOT committed to Git (see .gitignore);
they will be attached to a GitHub release once the reference is finalized.

## input/ — frozen GFS input (archived 2026-07-10)

Three GRIB2 files from the NOMADS GFS 0p25 grib filter, cycle **2026-07-09 06z**,
valid times 06/12/18 UTC on 2026-07-09 (forecast hours f000/f006/f012), with the
level/variable subset defined by `GfsData().g_grib_url_levels` /
`g_grib_url_meteovars` (neural_network/inc/dataset.py):

    2026-07-09-06   f000
    2026-07-09-12   f006
    2026-07-09-18   f012

Archived immediately because NOMADS retains cycles for only ~10 days.
Re-created via `Forecast.download_forecast('2026070906', '0p25', h, 6, dest)`
for h in {0, 6, 12}.

These files are meant to be fed through the `forced_meteo_files` seam in
`neural_network/forecast.py` (expects exactly 3 files) to make pipeline runs
reproducible without network access.

## run1_provisional/ — output of the first successful pipeline run (2026-07-10)

Output of unmodified `forecast.py` (commit af97c07 environment, live download,
cycle mix as fetched at run time — NOT yet the deterministic reference):

- `predictions.txt` — raw forecast output, input of the C++ tiler
- `tilerArguments.json` — tiler invocation arguments
- `spots.json` — per-spot forecast as served by the website (valid 2026-07-09)

## reference/ — the frozen golden master (stage A3, finalized 2026-07-10)

Produced by `run_golden_master.py` on the frozen input above: the pipeline
runs without network access via the `forced_meteo_files` seam, with fixed
seeds, `TF_DETERMINISTIC_OPS=1`, single-threaded TensorFlow and
`PYTHONHASHSEED=0`, for exactly one valid day (2026-07-09).

**Determinism result:** three independent runs produced byte-identical
`predictions.txt` (identical MD5) and equivalent tiles and spots.json.
The pipeline is fully deterministic on an unchanged environment.

**Calibrated tolerances** for `compare_golden_master.py` (defaults):

- predictions.txt / spots.json: `rtol=1e-5`, `atol=2e-6`. On identical
  hardware the observed deviation is exactly 0 (byte-identical). Across
  hardware (GitHub CI vs. development machine) 1-ulp float drift flips the
  last printed digit (resolution 1e-6 at 6 decimals) on ~0.06% of lines —
  the first CI run demonstrated this on 2026-07-10; atol=2e-6 covers a
  last-digit flip including rounding-boundary cases.
- tiles: max channel difference 2, at most 0.1 % differing pixels per tile,
  deterministic sample of ~50 tiles across all zoom levels.

**Usage:**

    # inside the container
    python golden_master/run_golden_master.py golden_master/runs/<name>
    python golden_master/compare_golden_master.py \
        golden_master/reference golden_master/runs/<name>

Any change to the pipeline (stages B-E) must keep this comparison green;
tolerance changes are their own, justified commits (never silent).

Training remains outside the golden-master scope: it is inherently
non-deterministic (multi-init, early stopping) and out of scope of the
modernization anyway; the shipped `.npy` weights are treated as a frozen,
irreplaceable artifact.

## Corner cache — frozen artifact of the removed C++ tiler (stage D1)

Since stage D1 the tiles are rendered by the Python port
(`pipeline/tiler.py`); the C++/Qt tiler has been removed from the tree.
The per-tile corner cache it produced (`tiler/_cache/256/…`, int32
big-endian, 4 cell-corner indices per pixel) is preserved as the release
asset **gm_corner_cache.tar.gz** and should be extracted on every fresh
clone (see CLAUDE.md / the CI workflow).

The cache is technically recomputable: the Python port contains a faithful
fallback (`compute_corners_scalar`) that was verified to reproduce the C++
cache byte-identically on zoom 5–8 tiles and the vignette. It is kept as a
frozen artifact anyway because (a) recomputing all 1352 files is slow
(~1.3 s per tile) and (b) the C++ `std::sort` is unstable, so at exact
float32 distance ties the fallback (stable argsort) could in principle
choose different corners — no such tie occurs in the frozen data, but the
original bytes are the safer reference.

**D1 acceptance check** (Python tiler vs. C++ reference on identical
`predictions.txt`, ALL tiles, stricter than the golden-master tile
tolerance):

    python golden_master/compare_tiler_outputs.py \
        <run>/tiles golden_master/reference/tiles/2026-07-09/256

Result 2026-07-11: 2521/2703 PNGs byte-identical pixels, 182 within ±1 in
one channel (226 of 177 million pixels; cause: 1-ulp sin() difference
numpy vs. libm at truncation boundaries of the fufu pattern), all 269
.data tiles byte-identical.
