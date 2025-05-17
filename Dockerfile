# 1) CSS ビルド用ステージ
FROM node:18-alpine AS css-builder
WORKDIR /src
COPY builder/package.json builder/tailwind.config.js builder/postcss.config.js ./
COPY builder/input.css ./src/input.css
RUN npm install
RUN mkdir -p /build/css
RUN npx tailwindcss -i src/input.css -o /build/css/main.css --minify

# 2) 本番コンテナ
FROM python:3.13-slim-bullseye

# システム依存関係インストール
RUN apt-get update && apt-get install -y curl && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# タイムゾーン設定
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Poetry インストール
RUN curl -sSL https://install.python-poetry.org | python3 - && \
  python3 -m pip install --no-cache-dir --upgrade pip
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
# 依存関係インストール
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
  poetry install --no-root --no-interaction --no-ansi

# アプリケーションコード
COPY ./app ./app
COPY ./scripts ./scripts

# CSS 成果物をコピー
RUN mkdir -p /app/app/static/css
COPY --from=css-builder /build/css/main.css /app/app/static/css/main.css

# 既存の JS ライブラリ取得（htmx, Alpine）
RUN mkdir -p /app/app/static/js && \
  curl -Lo /app/app/static/js/htmx.min.js https://unpkg.com/htmx.org/dist/htmx.min.js && \
  curl -Lo /app/app/static/js/alpine.min.js https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]