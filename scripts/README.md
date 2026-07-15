# Scripts

## To be executed once

```bash
python download_data.py             # Download training weather and flights data (200MB)
python download_elevation_tiles.py  # Download elevation data (260MB)
python download_background_tiles.py # Download background tiles (facultative) (180MB)

python download_GFS.py # Optional, download the source .grib weather data files from GFS
```

## To be executed once per session

```bash
sh start_jupyter.sh # Start Jupyter server for the neural network documentation
                    # NOTE: jupyter is no longer in the image, see the script
```

Der Apache-Startbefehl entfiel 2026-07: Die Webschicht ist FastAPI
(`web/app.py`), gestartet über `docker compose up -d web`.

## To be executed if needed

```bash
sh update_nn_README.sh # If you have modified the neural network documentation
```
