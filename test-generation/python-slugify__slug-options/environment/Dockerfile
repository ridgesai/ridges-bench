FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0 \
    text-unidecode==1.3

# python-slugify v9.1.1
RUN git clone https://github.com/un33k/python-slugify.git /app \
    && git -C /app checkout 6aa0b0f688e67a3e6c28b7a96749cad2afb28ad8 \
    && test -z "$(git -C /app status --porcelain)" \
    && mkdir -p /app/regression_tests

ENV PYTHONPATH=/app
WORKDIR /app
