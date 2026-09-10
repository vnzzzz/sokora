# 1) frontend assetビルド用ステージ
FROM node:22-bookworm-slim AS assets-builder
WORKDIR /src
COPY builder ./builder
COPY app ./app
COPY scripts/build_assets.sh ./scripts/build_assets.sh
RUN chmod +x ./scripts/build_assets.sh && ./scripts/build_assets.sh

# 2) 開発コンテナ
FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

# uv を固定バージョンで導入
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/

# sokora固有の開発ツール。Agent/Codex/Claude/GitHub CLI等はagent-dev Featureが管理する。
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  vim \
  nano \
  bash-completion \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# タイムゾーンをAsia/Tokyoに設定
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app
COPY ./scripts ./scripts

# workspace bind mountで隠れない場所に開発用virtualenvを作る。
ENV UV_PROJECT_ENVIRONMENT=/opt/sokora-venv
ENV UV_CACHE_DIR=/home/vscode/.cache/uv
ENV PATH="/opt/sokora-venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked

# Playwright browserをremoteUserに依存しない共有パスへ配置する。
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN uv run python -m playwright install --with-deps && \
  chmod -R a+rX /ms-playwright

# runtime用ディレクトリ、uv環境、cache mount先をvscodeユーザーで利用可能にする。
RUN mkdir -p \
  /app/assets/css \
  /app/assets/js \
  /app/assets/json \
  /app/data \
  /home/vscode/.cache/uv && \
  chown -R vscode:vscode /app/data /home/vscode/.cache /opt/sokora-venv

# 祝日データをビルド時に取得
RUN python3 scripts/build_holiday_cache.py

# productionと同じbuild scriptで生成したfrontend assetsをコピー
COPY --from=assets-builder /src/assets/css/main.css /app/assets/css/main.css
COPY --from=assets-builder /src/assets/js/htmx.min.js /app/assets/js/htmx.min.js
COPY --from=assets-builder /src/assets/js/alpine.min.js /app/assets/js/alpine.min.js

EXPOSE 8000

# devcontainer 起動時はアイドル状態とし、アプリは make run で起動する
CMD ["sleep", "infinity"]
