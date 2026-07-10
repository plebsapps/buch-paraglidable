# predictions.txt — the forecast→tiler interchange format

Reverse-engineered specification of the previously undocumented ad-hoc format
(stage C1 of the modernization). Ground truth: the writer
`GridLatLon.export_data_for_tiler` (`neural_network/inc/grid_latlon.py`),
the column semantics in `Predict.compute_prediction_file_cells`
(`neural_network/inc/predict.py`), and the reader `MapData::readFile`
(`tiler/Tiler/main.cpp`).

A Python reader/writer implementing this spec lives in
`pipeline/predictions_io.py` (round-trip tested against the golden-master
reference). The future Python tiler (stage D) reads this format; in stage E
its content moves to PostgreSQL via expand and contract.

## Container format

- Plain text, one line per non-empty forecast grid cell, `\n` line endings.
- Fields separated by a **single space**; no header, no comments.
- Every field is formatted with C `%f` (fixed notation, **6 decimal places**).
- Line structure: `lat lon v0 v1 ... v27` — 30 fields total in the current
  pipeline. The C++ reader accepts any number of value fields (>= 1) and
  ignores lines with fewer than 3 fields; the value count is not declared
  anywhere, consumers must know it.
- `lat`/`lon` are the **cell centers** of a 0.25° x 0.25° grid with a
  -0.125° offset in both axes (`grid_desc_predictions = (0.25, 0.25,
  -0.125, -0.125)` in `forecast.py`); latitude descends from north to south
  in writer order, longitude covers the two GRIB crops (western Europe /
  eastern Atlantic wrap).
- Reference size: 33 666 lines for the two crops of the current pipeline.

## Value columns (v0..v27)

Pressure levels are always ordered 1000, 900, 800, 700, 600 hPa; all
meteorological inputs are the 12h forecast values.

| Index | Content | Source |
|---|---|---|
| v0-v4 | Geopotential height [gpm] at 1000/900/800/700/600 hPa | GRIB (not predicted) |
| v5-v9 | Flyability in [0,1] at 1000/900/800/700/600 hPa | neural network output 0 |
| v10 | Crossability in [0,1], mean over the 5 levels | neural network output 1 |
| v11-v15 | Predicted wind at 1000/900/800/700/600 hPa | neural network output 2 |
| v16 | Humidity, mean over the 5 levels | neural network output 3 |
| v17 | Attractiveness — always `0.000000` (reserved) | constant in predict.py |
| v18-v22 | Wind U component [m/s] at 1000/900/800/700/600 hPa | GRIB (not predicted) |
| v23-v27 | Wind V component [m/s] at 1000/900/800/700/600 hPa | GRIB (not predicted) |

## Reader tolerances (C++ tiler behavior, to be preserved)

- Splits on a single space (`line.split(" ")`); consecutive spaces would
  produce empty fields and misparse — the writer never emits them.
- Lines with fewer than 3 fields are silently skipped.
- Values are parsed as 32-bit `float` (`toFloat()`), i.e. the reader is less
  precise than the writer; consumers must not rely on more than ~7
  significant digits.
- The reader recomputes its own bounding box from the data; ordering of the
  lines is not part of the contract for the tiler, but `predictions_io`
  preserves it for byte-identical round-trips.
