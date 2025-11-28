# 1) CSS ビルド用ステージ
FROM node:18-bookworm-slim AS css-builder
WORKDIR /src
COPY builder/package.json builder/tailwind.config.js builder/postcss.config.js ./
COPY builder/input.css ./src/input.css
RUN npm install
RUN mkdir -p /build/css
RUN npx tailwindcss -i src/input.css -o /build/css/main.css --minify

# 2) 開発コンテナ
FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

# 開発用のツールインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  curl \
  vim \
  nano \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# タイムゾーンをAsia/Tokyoに設定
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Poetryのインストール（グローバルに）
RUN curl -sSL https://install.python-poetry.org | python3 - && \
  python3 -m pip install --no-cache-dir --upgrade pip
ENV PATH="/root/.local/bin:$PATH"

# 開発ツールをグローバルにインストール
RUN pip install --no-cache-dir black isort mypy flake8

WORKDIR /app
COPY ./scripts ./scripts

# 依存関係ファイルのコピー
COPY pyproject.toml poetry.lock* README.md ./

# 依存関係のインストール
RUN poetry config virtualenvs.create false && \
  poetry install --no-root --no-interaction --no-ansi --with dev

# （必要であれば）Playwright を使う場合の依存インストール
# ※ pyproject.toml に playwright が入っている前提
RUN poetry run playwright install --with-deps

# 静的ファイル用ディレクトリを作成
RUN mkdir -p /app/assets/css /app/assets/js /app/assets/json

# 祝日データをビルド時に取得
RUN python3 scripts/build_holiday_cache.py

# CSS 成果物をコピー
COPY --from=css-builder /build/css/main.css /app/assets/css/main.css

# フロントエンドライブラリの取得
RUN curl -Lo /app/assets/js/htmx.min.js https://unpkg.com/htmx.org/dist/htmx.min.js && \
  curl -Lo /app/assets/js/alpine.min.js https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js

EXPOSE 8000

# devcontainer 起動時はアイドル状態とし、アプリは make run で起動する
CMD ["sleep", "infinity"]
