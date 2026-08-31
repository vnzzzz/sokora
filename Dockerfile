FROM node:22-bookworm-slim AS assets-builder
WORKDIR /app
COPY builder/package.json builder/package-lock.json builder/tailwind.config.js builder/postcss.config.js builder/input.css ./builder/
COPY scripts/build_assets.sh ./scripts/build_assets.sh
COPY app ./app
RUN chmod +x ./scripts/build_assets.sh && ./scripts/build_assets.sh

FROM python:3.13-slim-bookworm AS python-builder
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/sokora-venv \
    PATH="/opt/sokora-venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY scripts/build_holiday_cache.py ./scripts/build_holiday_cache.py
RUN python scripts/build_holiday_cache.py

FROM python:3.13-slim-bookworm AS runtime
ENV TZ=Asia/Tokyo \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/sokora-venv/bin:$PATH" \
    PORT=8000
WORKDIR /app

COPY --from=python-builder /opt/sokora-venv /opt/sokora-venv
COPY ./app ./app
COPY ./scripts/migration ./scripts/migration
COPY ./scripts/seeding/data_seeder.py ./scripts/seeding/data_seeder.py
COPY --from=assets-builder /app/assets ./assets
COPY --from=python-builder /app/assets/json/holidays_cache.json ./assets/json/holidays_cache.json
COPY ./docker/docker-entrypoint.sh /app/docker-entrypoint.sh

RUN mkdir -p /app/data && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c 'import http.client, os; connection = http.client.HTTPConnection("127.0.0.1", int(os.environ.get("PORT", "8000")), timeout=3); connection.request("GET", "/healthz"); response = connection.getresponse(); raise SystemExit(0 if response.status == 200 else 1)'

ENTRYPOINT ["/app/docker-entrypoint.sh"]
