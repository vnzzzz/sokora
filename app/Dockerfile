FROM python:3.13-slim

# システムの依存関係インストール
RUN apt-get update && apt-get install -y curl && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Poetry インストール
RUN curl -sSL https://install.python-poetry.org | python3 - && \
  python3 -m pip install --no-cache-dir --upgrade pip
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 依存関係ファイルのコピー
COPY pyproject.toml poetry.lock* ./

# 依存関係インストール
RUN poetry config virtualenvs.create false && \
  poetry install --no-root --no-interaction --no-ansi

# アプリケーションコードのコピー
COPY . .

# フロントエンドライブラリ取得
RUN curl -Lo /app/src/static/js/htmx.min.js https://unpkg.com/htmx.org/dist/htmx.min.js && \
  curl -Lo /app/src/static/js/alpine.min.js https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
