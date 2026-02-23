FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpulse0 \
    libportaudio2 \
    portaudio19-dev \
    wl-clipboard \
    libnotify-bin \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy UV_CACHE_DIR=/tmp/uv-cache
RUN mkdir -p /tmp/uv-cache && chmod 777 /tmp/uv-cache

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app/ app/
COPY prompts/ prompts/
RUN uv sync --frozen

ENTRYPOINT ["uv", "run"]
CMD ["python", "-m", "babel_tower.cli", "daemon"]