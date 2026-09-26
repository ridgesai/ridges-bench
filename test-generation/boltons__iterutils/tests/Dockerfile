FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0
RUN git clone https://github.com/mahmoud/boltons.git /matrix/clone && git -C /matrix/clone checkout 4332b35a278d694f30c99881faa61cde695c7a96
COPY *.patch /matrix/
RUN set -e; for s in pristine mutant_1 mutant_2 mutant_3 mutant_4 mutant_5 mutant_6 mutant_7 mutant_8 decoy_1 decoy_2 decoy_3; do \
      mkdir -p /matrix/$s/src && cp -r /matrix/clone/boltons /matrix/$s/src/boltons; \
      if [ "$s" != pristine ]; then (cd /matrix/$s/src && git apply -p1 /matrix/$s.patch); fi; \
    done; rm -f /matrix/*.patch
RUN git clone https://github.com/mahmoud/boltons.git /app && git -C /app checkout 4332b35a278d694f30c99881faa61cde695c7a96 \
    && git -C /app config user.email "verifier@example.com" && git -C /app config user.name "verifier" \
    && test -z "$(git -C /app status --porcelain)" && mkdir -p /app/regression_tests
COPY test.sh sample.env /tests/
RUN chmod +x /tests/test.sh
WORKDIR /app
