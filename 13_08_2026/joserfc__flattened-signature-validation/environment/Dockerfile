FROM ubuntu:24.04@sha256:561618e2c15bf2397621dd04f96926663a3b5616c189cf7e38db7e82f5c538ea

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates patch python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY constraints.txt /tmp/constraints.txt

RUN git clone --filter=blob:none https://github.com/authlib/joserfc.git src && \
    cd src && \
    git fetch --depth 1 origin 4dcd3635c65298d26869bac382aaf1435def68e1 && \
    git checkout --detach FETCH_HEAD

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -c /tmp/constraints.txt pip==24.0 wheel==0.48.0 && \
    /opt/venv/bin/pip install --no-cache-dir -c /tmp/constraints.txt pytest ruff==0.15.17 && \
    /opt/venv/bin/pip install --no-cache-dir -c /tmp/constraints.txt -e '/app/src[drafts]' && \
    /opt/venv/bin/pip check && \
    ln -s /opt/venv/bin/ruff /usr/local/bin/ruff && \
    ln -s /opt/venv/bin/pytest /usr/local/bin/pytest

RUN useradd -m -s /bin/bash agent && \
    chown -R root:root /opt/venv && \
    chmod -R go-w /opt/venv && \
    rm -rf /app/src/.git /app/src/.pytest_cache /app/src/.ruff_cache && \
    find /app/src -type d -name __pycache__ -prune -exec rm -rf {} + && \
    find /app/src -type f -name '*.py[co]' -delete && \
    cd /app/src && \
    git init -q && \
    git config user.email ridges@example.invalid && \
    git config user.name 'Ridges Baseline' && \
    git config commit.gpgsign false && \
    git add -A && \
    git commit -q --allow-empty -m 'ridges baseline' && \
    chown -R agent:agent /app/src

ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONPATH=/app/src
WORKDIR /app/src
