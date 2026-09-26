FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0

ARG COMMIT=d9503c08f8f83ce8a89bfcc45fec136868756243
RUN git clone https://github.com/SethMMorton/natsort.git /matrix/clone \
    && git -C /matrix/clone checkout ${COMMIT}

COPY *.patch /matrix/
RUN set -e; for state in pristine mutant_1 mutant_2 decoy_1 decoy_2; do \
        mkdir -p /matrix/$state/src; \
        cp -r /matrix/clone/natsort /matrix/$state/src/natsort; \
        if [ "$state" != pristine ]; then (cd /matrix/$state/src && git apply -p1 /matrix/$state.patch); fi; \
    done; \
    rm -f /matrix/*.patch

RUN git clone https://github.com/SethMMorton/natsort.git /app \
    && git -C /app checkout ${COMMIT} \
    && git -C /app config user.email "verifier@example.com" \
    && git -C /app config user.name "verifier" \
    && test -z "$(git -C /app status --porcelain)" \
    && mkdir -p /app/regression_tests

COPY test.sh sample.env /tests/
RUN chmod +x /tests/test.sh
WORKDIR /app
