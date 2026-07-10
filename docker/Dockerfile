FROM tensorflow/tensorflow:latest-py3

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
RUN sudo pip install tqdm colorama requests pandas matplotlib pillow numba pyproj jupyter
RUN sudo pip install pygrib
# Pinned 2026-07: current basemap master requires setuptools>=67 which does
# not exist for the Python 3.6 in this image. v1.2.1rel matches the
# basemap==1.2.1 recorded in python_requirements.txt (Jan 2020 freeze).
RUN sudo pip install https://github.com/matplotlib/basemap/archive/v1.2.1rel.zip

