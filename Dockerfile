## OpenHEMS-sample Docker pour add-on Home Assistant
## Basé sur l'image officielle base-debian (multi-arch)
## https://github.com/home-assistant/docker-base

FROM ghcr.io/home-assistant/base-debian:trixie

ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH:?}

WORKDIR /app

RUN curl https://www.google.com/
# RUN sed -i 's/deb.debian.org/http.debian.net/g' /etc/apt/sources.list.d/debian.sources

# Installation des dépendances système nécessaires (beaucoup sont déjà présentes)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  libffi-dev \
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
  libopenblas-dev \
  python3.13-venv \
  && rm -rf /var/lib/apt/lists/*

# Spécificité hdf5 (pour que Python trouve les en-têtes)
RUN ln -s /usr/include/hdf5/serial /usr/include/hdf5/include && export HDF5_DIR=/usr/include/hdf5

# Installation de uv (gestionnaire de paquets Python rapide)
ADD https://astral.sh/uv/install.sh /tmp/uv-install.sh
RUN chmod +x /tmp/uv-install.sh && /tmp/uv-install.sh && rm /tmp/uv-install.sh
ENV PATH="/root/.local/bin:$PATH"

# Copie des fichiers de dépendances
COPY pyproject.toml uv.lock* /app/

# Génération d'un requirements.txt à partir du lock file (ou pyproject.toml)
RUN if [ -f uv.lock ]; then \
      uv export --no-dev --frozen -o requirements.txt; \
    else \
      uv export --no-dev -o requirements.txt; \
    fi

RUN rm -rf .venv

RUN uv venv --python 3.13

# Installation des dépendances Python avec uv
# Pour les architectures ARM 32 bits (armv7), on utilise piwheels
RUN if [[ "${TARGETARCH}" == "armhf" || "${TARGETARCH}" == "armv7" ]]; then \
      uv pip install --index-url https://www.piwheels.org/simple -r requirements.txt; \
    else \
      uv pip install -r requirements.txt; \
    fi

# Symlink pour CBC (coinor-cbc) pour pulp sur ARM 32 bits
RUN if [[ "${TARGETARCH}" == "armhf" || "${TARGETARCH}" == "armv7" ]]; then \
      mkdir -p /usr/local/lib/python3.12/site-packages/pulp/solverdir/cbc/linux/32/ && \
      ln -sf /usr/bin/cbc /usr/local/lib/python3.12/site-packages/pulp/solverdir/cbc/linux/32/cbc || echo "cbc symlink ok"; \
    fi

# Correction scipy sur armv7 (nécessite libatomic)
RUN if [[ "${TARGETARCH}" == "armv7" ]]; then \
      apt-get update && apt-get install -y libatomic1 && rm -rf /var/lib/apt/lists/*; \
    fi

# Nettoyage des packages de compilation (inutiles en runtime)
RUN apt-get purge -y --auto-remove \
  gcc patchelf cmake meson ninja-build build-essential pkg-config gfortran \
  netcdf-bin libnetcdf-dev \
  && rm -rf /var/lib/apt/lists/*

# Création des dossiers nécessaires
RUN mkdir -p /app/data/ /log/ /share/openhems/ /share/emhass/

# Copie du reste du code source
ADD . /app/

# Installation finale du package openhems (sans ses dépendances, déjà installées)
RUN uv pip install --no-deps .

# Variables d'environnement Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Labels obligatoires pour un add-on Home Assistant
LABEL \
    io.hass.name="openhems" \
    io.hass.description="OpenHEMS: Home Energy Management System based on Home Assistant" \
    io.hass.version="0.2.16.2" \
    io.hass.type="addon" \
    io.hass.arch="amd64|arm64|armv7"

EXPOSE 8000
VOLUME /log /app/config

# Point d'entrée (adaptez le chemin si nécessaire)
ENTRYPOINT ["python", "/app/src/openhems/main.py", "-l", "/log/openhems.log", "--docker"]

