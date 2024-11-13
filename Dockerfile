## OpenHEMS-sample Docker
# https://masterdaweb.com/en/blog/fixing-requested-access-to-the-resource-is-denied-in-docker/
## Docker run addon testing example:
  ## docker build -t openhems .
  ## OR docker build --build-arg TARGETARCH=amd64 -t openhems .
  ## docker tag openhems openhomesystem22/openhems:latest
  ## docker push  openhomesystem22/openhems:latest
  ## docker run -d --name openhems openhems
  ## docker exec -it openhems bash
  ## docker run --rm -it -p 8000:8000 --name openhems openhems:latest
  ## docker run --rm -it -p 8000:8000 --name openhems -v ./config/:/app/config/ -v /var/log/openhems:/log openhems:latest

# armhf,amd64,armv7,aarch64
ARG TARGETARCH
# armhf=raspbian, amd64,armv7,aarch64=debian
ARG os_version=debian
# if (TARGETARCH==armhf)
# 	{os_version=raspbian}

FROM ghcr.io/home-assistant/$TARGETARCH-base-$os_version:bookworm AS base

# check if TARGETARCH was passed by build-arg
ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH:?}

WORKDIR /app
COPY requirements.txt /app/

# apt package install
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  libffi-dev \
  python3 \
  python3-pip \
  python3-dev \
  git \
  gcc \
  patchelf \
  cmake \
  meson \
  ninja-build \
  build-essential \
  libhdf5-dev \
  libhdf5-serial-dev \
  pkg-config \
  gfortran \
  netcdf-bin \
  libnetcdf-dev \
  coinor-cbc \
  coinor-libcbc-dev \
  libglpk-dev \
  glpk-utils \
  libatlas-base-dev \
  libopenblas-dev
# specify hdf5
RUN ln -s /usr/include/hdf5/serial /usr/include/hdf5/include && export HDF5_DIR=/usr/include/hdf5

# install packages from pip, use piwheels if arm 32bit
RUN [[ "${TARGETARCH}" == "armhf" || "${TARGETARCH}" == "armv7" ]] &&  pip3 install --index-url=https://www.piwheels.org/simple --no-cache-dir --break-system-packages -r requirements.txt ||  pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# try, symlink apt cbc, to pulp cbc, in python directory (for 32bit)
RUN [[ "${TARGETARCH}" == "armhf" || "${TARGETARCH}" == "armv7"  ]] &&  ln -sf /usr/bin/cbc /usr/local/lib/python3.11/dist-packages/pulp/solverdir/cbc/linux/32/cbc || echo "cbc symlink didnt work/not required"

# if armv7, try install libatomic1 to fix scipy issue
RUN [[ "${TARGETARCH}" == "armv7" ]] && apt-get update && apt-get install libatomic1 || echo "libatomic1 cant be installed"

# remove build only packages
RUN apt-get purge -y --auto-remove \
  gcc \
  patchelf \
  cmake \
  meson \
  ninja-build \
  build-essential \
  pkg-config \
  gfortran \
  netcdf-bin \
  libnetcdf-dev \
  && rm -rf /var/lib/apt/lists/*

# make sure data directory exists
RUN mkdir -p /app/data/
RUN mkdir -p /log/

# make sure emhass share directory exists
RUN mkdir -p /share/openhems/
RUN mkdir -p /share/emhass/

# copy required sources files
ADD . /app/
# COPY readme.md /app/
# COPY setup.py /app/
# COPY src/openhems/ /app/src/openhems/
# COPY src/openhems/modules/ /app/src/openhems/modules/
# COPY src/openhems/modules/energy_strategy/ /app/src/openhems/modules/energy_strategy/
# COPY src/openhems/modules/network/ /app/src/openhems/modules/network/
# COPY src/openhems/modules/util/ /app/src/openhems/modules/util/
# COPY src/openhems/modules/web/ /app/src/openhems/modules/web/
# COPY src/openhems/modules/network/driver/ /app/src/openhems/modules/network/driver/
# COPY src/openhems/modules/energy_strategy/driver/ /app/src/openhems/modules/energy_strategy/driver/

# EMHASS
# COPY lib/emhass/src/emhass/ /app/lib/emhass/src/emhass/
# COPY lib/emhass/src/emhass/templates/ /app/lib/emhass/src/emhass/templates/
# COPY lib/emhass/src/emhass/static/ /app/lib/emhass/src/emhass/static/
# COPY lib/emhass/src/emhass/static/data/ /app/lib/emhass/src/emhass/static/data/
# COPY lib/emhass/src/emhass/static/img/ /app/lib/emhass/src/emhass/static/img/
# COPY lib/emhass/src/emhass/data/ /app/lib/emhass/src/emhass/data/
# pre generated optimization results 
# COPY lib/emhass/data/opt_res_latest.csv /app/lib/emhass/data/
# COPY lib/emhass/README.md /app/lib/emhass/
# COPY lib/emhass/setup.py /app/lib/emhass/
# secrets file (secrets_emhass.yaml) can be copied into the container with volume mounts with docker run
# options.json file will be automatically generated and passed from Home Assistant using the addon

#set python env variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Docker Labels for hass
LABEL \
    io.hass.name="openhems" \
    io.hass.description="OpenHEMS: Home Energy Management System based on Home Assistant" \
    io.hass.version=${BUILD_VERSION} \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64|armhf|armv7"

EXPOSE 8000
VOLUME /log
VOLUME /app/config

# build OpenHEMS
# RUN pip3 install --no-cache-dir --break-system-packages --no-deps --force-reinstall  .
# ENTRYPOINT [ "python3", "-m", "openhems.main"]
ENTRYPOINT ["/app/src/openhems/main.py", "-l", "/log/openhems.log"]

# for running Unittest
#COPY tests/ /app/tests
#RUN apt-get update &&  apt-get install python3-requests-mock -y
#COPY data/ /app/data/
#ENTRYPOINT ["python3","-m","unittest","discover","-s","./tests","-p","test_*.py"]
