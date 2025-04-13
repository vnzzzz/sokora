FROM python:3.13-slim

# 1) apt-get update & curl
RUN apt-get update && apt-get install -y curl

# 2) Poetry インストール
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 3) ソースをコピー
COPY . /app

# 4) Poetryで依存解決
RUN poetry install --no-root

# 5) ミニファイドJSライブラリを取得(HTMX, Alpine.js, Chart.js)
RUN curl -Lo /app/src/static/js/htmx.min.js    https://unpkg.com/htmx.org/dist/htmx.min.js \
  && curl -Lo /app/src/static/js/alpine.min.js  https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js \
  && curl -Lo /app/src/static/js/chart.min.js   https://cdn.jsdelivr.net/npm/chart.js@4.2.1/dist/chart.umd.min.js

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
