# 1) アセットビルド用ステージ
FROM node:18-bookworm-slim AS assets-builder
WORKDIR /app
COPY builder/package.json builder/package-lock.json builder/tailwind.config.js builder/postcss.config.js builder/input.css ./builder/
COPY scripts/build_assets.sh ./scripts/build_assets.sh
COPY app ./app
RUN chmod +x ./scripts/build_assets.sh
RUN ./scripts/build_assets.sh

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

# CSS/JS 成果物をコピー
COPY --from=assets-builder /app/assets /app/assets

# 祝日データをビルド時に取得
RUN python3 scripts/build_holiday_cache.py

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
