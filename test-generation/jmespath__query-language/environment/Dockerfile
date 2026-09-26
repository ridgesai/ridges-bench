FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 pygments==2.21.0

RUN git clone https://github.com/jmespath/jmespath.py.git /app \
    && git -C /app checkout 6ff419a8b171d055a9bfc6904605bceb8b7a80ef \
    && test -z "$(git -C /app status --porcelain)" \
    && mkdir -p /app/regression_tests

ENV PYTHONPATH=/app
WORKDIR /app
