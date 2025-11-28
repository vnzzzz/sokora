# 1) CSS ビルド用ステージ
FROM node:18-bookworm-slim AS css-builder
WORKDIR /src
COPY builder/package.json builder/tailwind.config.js builder/postcss.config.js ./
COPY builder/input.css ./src/input.css
RUN npm install
RUN mkdir -p /build/css
RUN npx tailwindcss -i src/input.css -o /build/css/main.css --minify

# 2) 本番コンテナ
FROM python:3.13-slim-bookworm

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

# データディレクトリを用意
RUN mkdir -p /app/data

# 静的ファイル用ディレクトリを作成
RUN mkdir -p /app/assets/css /app/assets/js /app/assets/json

# 祝日データをビルド時に取得
RUN python3 scripts/build_holiday_cache.py

# CSS 成果物をコピー
COPY --from=css-builder /build/css/main.css /app/assets/css/main.css

# 既存の JS ライブラリ取得（htmx, Alpine）
RUN curl -Lo /app/assets/js/htmx.min.js https://unpkg.com/htmx.org/dist/htmx.min.js && \
  curl -Lo /app/assets/js/alpine.min.js https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js

# DB が無ければビルド時に初期化 + シーディング
RUN python3 - <<'PYCODE'
from app.db.session import initialize_database

initialize_database()
PYCODE

RUN if [ -f /app/data/sokora.db ]; then mkdir -p /app/seed && cp /app/data/sokora.db /app/seed/sokora.db; fi

COPY ./docker/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
