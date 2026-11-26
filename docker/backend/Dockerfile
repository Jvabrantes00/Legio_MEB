FROM python:3.12-slim-trixie

# Geração de PDF confirmada pelo humano em ARM64 no candidato anterior.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system sia \
    && useradd --system --gid sia --home-dir /app sia \
    && mkdir -p /app/media /home/sia/.cache \
    && chown sia:sia /app/media /home/sia/.cache \
    && chmod 700 /home/sia/.cache

ENV XDG_CACHE_HOME=/home/sia/.cache
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
USER sia
