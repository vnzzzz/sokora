# 1) フロントエンドasset build stage
# productionと同じbuild scriptを使い、devcontainerでも同じCSS/JS成果物を生成する。
FROM node:22-bookworm-slim AS assets-builder
WORKDIR /src
COPY builder ./builder
COPY app ./app
COPY scripts/build_assets.sh ./scripts/build_assets.sh
RUN chmod +x ./scripts/build_assets.sh && ./scripts/build_assets.sh

# 2) development container stage
# application sourceは起動時に/appへbind mountし、dependencyや開発toolはimage側で準備する。
FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

# uvはproduction Dockerfileと同じ固定versionを使用する。
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/

# sokora固有のOS toolだけを追加する。Agent/Codex/Claude/GitHub CLI等はagent-dev Featureが管理する。
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  vim \
  nano \
  bash-completion \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# local開発とapplication runtimeの時刻基準を揃える。
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app
COPY ./scripts ./scripts

# /appはworkspace bind mountで置き換わるため、virtualenvとuv cacheはmount外へ置く。
ENV UV_PROJECT_ENVIRONMENT=/opt/sokora-venv
ENV UV_CACHE_DIR=/home/vscode/.cache/uv
ENV PATH="/opt/sokora-venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked

# Playwright browserはremoteUserに依存しない共有pathへ配置する。
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN uv run python -m playwright install --with-deps && \
  chmod -R a+rX /ms-playwright

# bind mount後もvscode userがruntime data、uv cache、virtualenvを書き込めるようownershipを整える。
RUN mkdir -p \
  /app/assets/css \
  /app/assets/js \
  /app/assets/json \
  /app/data \
  /home/vscode/.cache/uv && \
  chown -R vscode:vscode /app/data /home/vscode/.cache /opt/sokora-venv

# productionと同様、runtimeで外部APIへ依存しないよう祝日cacheをbuild時に生成する。
RUN python3 scripts/build_holiday_cache.py

# productionと同じfrontend assetsをimageへ配置する。/appは起動時にworkspaceで置き換わる。
COPY --from=assets-builder /src/assets/css/main.css /app/assets/css/main.css
COPY --from=assets-builder /src/assets/js/htmx.min.js /app/assets/js/htmx.min.js
COPY --from=assets-builder /src/assets/js/alpine.min.js /app/assets/js/alpine.min.js

EXPOSE 8000

# devcontainerはidle状態で起動し、applicationはdeveloperがmake runで明示的に起動する。
CMD ["sleep", "infinity"]
