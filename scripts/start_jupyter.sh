# NOTE (2026-07-15, stage G): jupyter is no longer installed in the image.
# The original Dockerfile shipped it for the notebook workflow, but nothing in
# the forecast/tiler/web path imports it, and it carried 106 of the image's
# known vulnerabilities (see docs/abhaengigkeiten.md). To use notebooks again:
#   docker exec -it paraglidable sudo pip install jupyter
# Kept as documentation of the original workflow.
cd ../neural_network
jupyter notebook --ip=0.0.0.0 --port=8888
