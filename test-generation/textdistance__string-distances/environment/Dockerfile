FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0
RUN git clone https://github.com/life4/textdistance.git /app && git -C /app checkout faa25f6ff50d0f34dc9655d4d7b0d8daf6f9ff85 \
    && test -z "$(git -C /app status --porcelain)"
ENV PYTHONPATH=/app
RUN mkdir -p /app/regression_tests
WORKDIR /app
