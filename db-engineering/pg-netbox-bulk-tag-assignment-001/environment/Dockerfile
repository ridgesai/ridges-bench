FROM python:3.13.7-slim-bookworm@sha256:adafcc17694d715c905b4c7bebd96907a1fd5cf183395f0ebc4d3428bd22d92d

ARG SOURCE_REVISION=00791344e68213bde942218283dce03cc3941c30
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash build-essential ca-certificates curl git jq libpq-dev postgresql-client redis-tools \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/netbox-community/netbox.git /app \
    && git -C /app checkout --detach "$SOURCE_REVISION" \
    && test "$(git -C /app rev-parse HEAD)" = "$SOURCE_REVISION" \
    && test "$(sha256sum /app/LICENSE.txt | cut -d' ' -f1)" = "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594" \
    && rm -rf /app/.git

WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir ruff==0.15.2

COPY configuration.py /app/netbox/netbox/configuration.py
COPY baseline_mutation.py /usr/local/bin/baseline_mutation.py
RUN python /usr/local/bin/baseline_mutation.py \
    && rm /usr/local/bin/baseline_mutation.py

RUN useradd --create-home --uid 1000 --shell /bin/bash agent \
    && chown -R root:root /app \
    && chmod -R go-w /app \
    && chown root:agent /app/netbox/extras \
    && chmod 775 /app/netbox/extras \
    && chown agent:agent /app/netbox/extras/managers.py \
    && chmod 755 /app

CMD ["sh", "-c", "sleep infinity"]
