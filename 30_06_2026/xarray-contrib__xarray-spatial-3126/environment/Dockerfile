FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# System and Python build dependencies.
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
    (git fetch --depth 1 origin 455ee478f63b779f0264fafbf4782b5188ed52ed || git fetch --depth 1 origin "+refs/pull/3126/head:refs/remotes/origin/pr/3126") && \
    git checkout --detach FETCH_HEAD && \
    git submodule update --init --recursive

WORKDIR /app/src

ENV CI=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NUMBA_ENABLE_CUDASIM=1 \
    NUMBA_CACHE_DIR=/tmp/numba-cache \
    DASK_SCHEDULER=single-threaded \
    MPLBACKEND=Agg \
    PYTHONPATH="/opt/cupy_stub" \
    PATH="/opt/venv/bin:${PATH}"

# CPU-backed CuPy compatibility shim for CUDA simulator tests.
COPY cupy_stub /opt/cupy_stub

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

# Reset generated metadata so bug.patch applies cleanly.
RUN git reset --hard

# Apply bug.patch to revert to buggy state (BASE)
COPY bug.patch /tmp/bug.patch
RUN patch -p1 < /tmp/bug.patch && rm /tmp/bug.patch

RUN rm -rf /app/src/.git

WORKDIR /app/src
