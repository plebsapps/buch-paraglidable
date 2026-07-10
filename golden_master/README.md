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

The definitive golden master (deterministic run on input/, repeated 3x,
tolerances calibrated) is produced in stage A3.
