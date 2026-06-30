FROM ubuntu:24.04

# Base system packages (common to all languages)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    patch \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Clone repo at HEAD commit (with fix applied)
RUN git clone https://github.com/xarray-contrib/xarray-spatial.git src && \
    cd src && \
    (git fetch --depth 1 origin e60c936819b5c6cf97bbd9f1743510af7b08ab20 || git fetch --depth 1 origin "+refs/pull/3201/head:refs/remotes/origin/pr/3201") && \
    git checkout --detach FETCH_HEAD && \
    git submodule update --init --recursive

WORKDIR /app/src

ENV CI=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NUMBA_ENABLE_CUDASIM=1 \
    NUMBA_CACHE_DIR=/tmp/numba-cache \
    MPLBACKEND=Agg \
    PATH="/opt/venv/bin:${PATH}"

RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python \
        build \
        param \
        pyct \
        setuptools \
        setuptools_scm \
        wheel && \
    uv pip install --python /opt/venv/bin/python --no-build-isolation \
        -e ".[geotiff]" \
        "dask[array]" \
        pytest \
        rasterio \
        rioxarray \
        shapely \
        affine

# Run CuPy-backed regression tests in CPU-only Docker via a compatibility shim.
COPY cupy_stub/cupy /tmp/cupy
RUN cp -R /tmp/cupy /app/src/cupy

# Reset generated metadata so bug.patch applies cleanly.
RUN git reset --hard

# Apply bug.patch to revert to buggy state (BASE)
COPY bug.patch /tmp/bug.patch
RUN patch -p1 < /tmp/bug.patch && rm /tmp/bug.patch

RUN rm -rf /app/src/.git

WORKDIR /app/src
