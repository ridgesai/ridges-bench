FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 pygments==2.21.0

COPY sample.env *.patch /matrix/

RUN git clone https://github.com/jmespath/jmespath.py.git /matrix/clone \
    && git -C /matrix/clone checkout 6ff419a8b171d055a9bfc6904605bceb8b7a80ef \
    && . /matrix/sample.env \
    && for s in pristine $MUTANTS $DECOYS; do \
         mkdir -p /matrix/$s/src \
         && cp -r /matrix/clone/jmespath /matrix/$s/src/jmespath \
         && if [ "$s" != pristine ]; then (cd /matrix/$s/src && git apply -p1 /matrix/$s.patch); fi \
         || exit 1; \
       done \
    && rm -rf /matrix/clone /matrix/*.patch /matrix/sample.env

RUN git clone https://github.com/jmespath/jmespath.py.git /app \
    && git -C /app checkout 6ff419a8b171d055a9bfc6904605bceb8b7a80ef \
    && git -C /app config user.email "ridges@example.com" \
    && git -C /app config user.name "Ridges" \
    && test -z "$(git -C /app status --porcelain)" \
    && mkdir -p /app/regression_tests

COPY test.sh sample.env /tests/
RUN chmod +x /tests/test.sh

WORKDIR /app
