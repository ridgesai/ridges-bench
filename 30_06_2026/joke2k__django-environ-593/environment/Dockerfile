FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    patch \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Clone repo at HEAD commit (with fix applied)
RUN git clone https://github.com/joke2k/django-environ.git src && \
    cd src && \
    (git fetch --depth 1 origin b55c1b4ec7efb640e295f4cb82bac64019d52c4f || git fetch --depth 1 origin "+refs/pull/593/head:refs/remotes/origin/pr/593") && \
    git checkout --detach FETCH_HEAD && \
    git submodule update --init --recursive

WORKDIR /app/src

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python -e ".[testing]"

# Reset tracked files before applying the task's buggy-state patch.
RUN git reset --hard

# Apply bug.patch to revert to buggy state (BASE)
COPY bug.patch /tmp/bug.patch
RUN patch -p1 < /tmp/bug.patch && rm /tmp/bug.patch

RUN rm -rf /app/src/.git

WORKDIR /app/src
