FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0 \
    more-itertools==11.1.0 typeguard==4.6.0 typing_extensions==4.16.0

# inflect v7.5.0
RUN git clone https://github.com/jaraco/inflect.git /app \
    && git -C /app checkout c079a96a573ece60b54bd5210bb0f414beb74dcd \
    && test -z "$(git -C /app status --porcelain)" \
    && mkdir -p /app/regression_tests

ENV PYTHONPATH=/app
WORKDIR /app
