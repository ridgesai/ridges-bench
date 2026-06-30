FROM ubuntu:24.04

# System packages for cloning, patching, Python package builds, and terminal tests.
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    patch \
    build-essential \
    python3 \
    python3-dev \
    python3-venv \
    pkg-config \
    less \
    tmux \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

ENV UV_PYTHON=3.13 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    CI=true \
    PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# Clone repo at HEAD commit (with fix applied)
RUN git clone https://github.com/OpenHands/software-agent-sdk.git src && \
    cd src && \
    (git fetch --depth 1 origin 4ddce219e453a3fb75aa9e3200ee05d35aae229e || git fetch --depth 1 origin "+refs/pull/3652/head:refs/remotes/origin/pr/3652") && \
    git checkout --detach FETCH_HEAD && \
    git submodule update --init --recursive

WORKDIR /app/src

RUN uv python install 3.13 && \
    uv sync --frozen --group dev --python 3.13

# Reset tracked files so bug.patch applies to the cloned HEAD cleanly.
RUN git reset --hard

# Apply bug.patch to revert to buggy state (BASE)
COPY bug.patch /tmp/bug.patch
RUN patch -p1 < /tmp/bug.patch && rm /tmp/bug.patch

RUN rm -rf /app/src/.git

WORKDIR /app/src
