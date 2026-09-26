FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0

# natsort 8.4.0
RUN git clone https://github.com/SethMMorton/natsort.git /app \
    && git -C /app checkout d9503c08f8f83ce8a89bfcc45fec136868756243 \
    && test -z "$(git -C /app status --porcelain)" \
    && mkdir -p /app/regression_tests

ENV PYTHONPATH=/app
WORKDIR /app
