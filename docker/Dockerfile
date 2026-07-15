# Pinned 2026-07 by digest (stage B): "latest-py3" is a tag frozen in 2020
# (TensorFlow 2.1.0, Ubuntu 18.04, Python 3.6) but tags are mutable --
# the digest is the actual state the golden master was proven on.
FROM tensorflow/tensorflow:latest-py3@sha256:14ec674cefd622aa9d45f07485500da254acaf8adfef80bd0f279db03c735689

ARG USERNAME=paraglidable
RUN useradd -m $USERNAME
ENV HOME /home/$USERNAME

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get install -y --no-install-recommends net-tools libopenjp2-7-dev libpng-dev libpng16-16 vim sass wget qt5-default pdf2svg apache2 php libapache2-mod-php nodejs npm ibgeos-3.6.2 libgeos-dev unzip

# grib
RUN apt-get -y update && apt-get install -y --no-install-recommends libgrib-api-dev libgrib-api0
RUN apt-get -y update && apt-get install -y --no-install-recommends libeccodes-dev libeccodes0

# Added 2026-07: the tensorflow:latest-py3 base image ships no build tools,
# but scripts/build_tiler.sh needs make and g++ (qmake + make for the Qt tiler)
RUN apt-get -y update && apt-get install -y --no-install-recommends make g++

# tex2svg
# Disabled 2026-07: npm 3.x (Ubuntu 18.04) can no longer talk to the npm
# registry (TypeError inside npm itself), so this step breaks the build.
# mathjax-node-cli is only used by scripts/update_nn_README.py to regenerate
# the documentation equations; the resulting SVGs are already committed in
# neural_network/docs/README_files/. Not needed for forecast/tiler/www.
#RUN npm install -y --no-install-recommends --global mathjax-node-cli

# Add sudo support
RUN apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME


USER $USERNAME

# glob3 removed 2026-07: placeholder package deleted from PyPI; the code only
# uses the Python 3 stdlib module "glob" (see neural_network/plot_training.py)
# Pinned 2026-07 (stage B): install from the lockfile frozen out of the image
# state the golden master was proven on. apt-managed packages (pygobject,
# cryptography, ...) are excluded -- the base image digest pins those.
# python_requirements.txt remains as the author's historical Jan 2020 freeze.
# Slimmed 2026-07-15 (stage G): the original Dockerfile installed "jupyter"
# for the author's notebook workflow (scripts/start_jupyter.sh); the lockfile
# had frozen it plus ~50 transitive packages into the production image. No
# production code imports any of them, so they were dropped from the lockfile:
# 128 -> 63 packages, 106 fewer known vulnerabilities, image 5.78 -> 5.56 GB.
# Golden master EQUIVALENT with unchanged tolerances. idna is pinned
# explicitly because it used to arrive only via a jupyter dependency.
COPY python_requirements.lock.txt /tmp/python_requirements.lock.txt
RUN sudo pip install -r /tmp/python_requirements.lock.txt
# Pinned 2026-07: current basemap master requires setuptools>=67 which does
# not exist for the Python 3.6 in this image. v1.2.1rel matches the
# basemap==1.2.1 recorded in python_requirements.txt (Jan 2020 freeze).
RUN sudo pip install https://github.com/matplotlib/basemap/archive/v1.2.1rel.zip

