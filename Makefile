SHELL := /bin/bash

# Load .env when available so SERVICE_PORT and other env vars are reused.
ENV_FILE ?= .env
ENV_FILE_PATH := $(CURDIR)/$(ENV_FILE)
ifneq (,$(wildcard $(ENV_FILE_PATH)))
include $(ENV_FILE_PATH)
export
endif

SERVICE_PORT ?= 8000
IMAGE_NAME ?= sokora
DEV_IMAGE_NAME ?= sokora-dev
VERSION ?=
ifndef VERSION
$(error VERSION is not set. Define VERSION in .env)
endif
VERSION_TAG := $(IMAGE_NAME):$(VERSION)
CONTAINER_NAME ?= sokora
DEV_CONTAINER_NAME ?= sokora-dev
SEED_DAYS_BACK ?= 60
SEED_DAYS_FORWARD ?= 60
DOCKER_BUILD_PROXY_ARGS := $(if $(proxy),--build-arg proxy=$(proxy) --build-arg http_proxy=$(proxy) --build-arg https_proxy=$(proxy) --build-arg HTTP_PROXY=$(proxy) --build-arg HTTPS_PROXY=$(proxy),)
DOCKER_PROXY_ENV := $(if $(proxy),-e proxy=$(proxy) -e http_proxy=$(proxy) -e https_proxy=$(proxy) -e HTTP_PROXY=$(proxy) -e HTTPS_PROXY=$(proxy),)

.PHONY: help sync install run dev-shell seed test assets holiday-cache migrate lint format format-check typecheck quality build docker-build docker-build-proxy dev-build docker-run docker-run-proxy docker-stop

help:
	@printf "\nSokora make targets (devcontainer aware):\n"
	@printf "  make sync            Sync Python dependencies from uv.lock\n"
	@printf "  make install         Sync Python deps and npm packages for builder\n"
	@printf "  make run             Run FastAPI (devcontainer) with reload on SERVICE_PORT (default: 8000)\n"
	@printf "  make dev-shell       Attach to the running devcontainer (name: %s)\n" "$(DEV_CONTAINER_NAME)"
	@printf "  make seed            Seed attendance data (vars: SEED_DAYS_BACK, SEED_DAYS_FORWARD)\n"
	@printf "  make test            Run cleanup + API/unit + e2e tests\n"
	@printf "  make assets          Build CSS/JS into assets/ via builder\n"
	@printf "  make holiday-cache   Build holiday cache into assets/json/holidays_cache.json\n"
	@printf "  make migrate         Run Alembic migrations (upgrade head)\n"
	@printf "  make lint            Run Ruff lint and import checks\n"
	@printf "  make format          Apply Ruff import sorting and formatting\n"
	@printf "  make format-check    Check Ruff formatting without modifying files\n"
	@printf "  make typecheck       Run mypy\n"
	@printf "  make quality         Run lint + format-check + typecheck\n"
	@printf "  make build           Build production image (%s) from ./Dockerfile\n" "$(IMAGE_NAME)"
	@printf "  make dev-build       Build devcontainer image (%s) from .devcontainer/Dockerfile\n" "$(DEV_IMAGE_NAME)"
	@printf "  make docker-build    Build production image (%s) using VERSION tag from .env\n" "$(VERSION_TAG)"
	@printf "  make docker-build-proxy Build production image (%s) via Dockerfile.proxy with proxy args from .env\n" "$(VERSION_TAG)"
	@printf "  make docker-run      Run production container (tag: %s) with port mapping and data volume mount\n" "$(VERSION_TAG)"
	@printf "  make docker-run-proxy   Run production container (tag: %s) with proxy env from .env\n" "$(VERSION_TAG)"
	@printf "  make docker-stop     Stop and remove the production container\n\n"

sync:
	uv sync --locked

install: sync
	./scripts/build_assets.sh

run: prepare-dev-assets
	uv run uvicorn app.main:app --host 0.0.0.0 --port $(SERVICE_PORT) --reload

dev-shell:
	docker exec -it $(DEV_CONTAINER_NAME) bash

seed:
	mkdir -p data
	./scripts/seeding/run_seeder.sh $(SEED_DAYS_BACK) $(SEED_DAYS_FORWARD)

test: sync
	./scripts/testing/run_test.sh

assets:
	./scripts/build_assets.sh

prepare-dev-assets: sync
	./scripts/prepare_dev_assets.sh

holiday-cache: sync
	mkdir -p assets/json
	uv run python scripts/build_holiday_cache.py

migrate: sync
	PYTHONPATH=/app uv run alembic -c scripts/migration/alembic.ini upgrade head

lint: sync
	uv run ruff check app

format: sync
	uv run ruff check app --select I --fix
	uv run ruff format app

format-check: sync
	uv run ruff format --check app

typecheck: sync
	uv run mypy app

quality: lint format-check typecheck

build:
	docker build -t $(IMAGE_NAME) .

docker-build:
	docker build -t $(VERSION_TAG) .

docker-build-proxy:
	docker build $(DOCKER_BUILD_PROXY_ARGS) -f Dockerfile.proxy -t $(VERSION_TAG) .

dev-build:
	docker build -f .devcontainer/Dockerfile -t $(DEV_IMAGE_NAME) ..

docker-run: docker-build
	mkdir -p data
	@ENV_FILE_ARG=""; \
	if [ -f "$(ENV_FILE_PATH)" ]; then \
		echo "loading env from $(ENV_FILE_PATH)"; \
		set -a; . "$(ENV_FILE_PATH)"; set +a; \
		ENV_FILE_ARG="--env-file $(ENV_FILE_PATH)"; \
	fi; \
	docker run -d --name $(CONTAINER_NAME) $$ENV_FILE_ARG --rm \
		-p $${SERVICE_PORT:-$(SERVICE_PORT)}:8000 \
		-v $(abspath data):/app/data \
		$(VERSION_TAG)

docker-run-proxy: docker-build-proxy
	mkdir -p data
	@ENV_FILE_ARG=""; \
	if [ -f "$(ENV_FILE_PATH)" ]; then \
		echo "loading env from $(ENV_FILE_PATH)"; \
		set -a; . "$(ENV_FILE_PATH)"; set +a; \
		ENV_FILE_ARG="--env-file $(ENV_FILE_PATH)"; \
	fi; \
	docker run -d --name $(CONTAINER_NAME) $$ENV_FILE_ARG $(DOCKER_PROXY_ENV) --rm \
		-p $${SERVICE_PORT:-$(SERVICE_PORT)}:8000 \
		-v $(abspath data):/app/data \
		$(VERSION_TAG)

docker-stop:
	-docker stop $(CONTAINER_NAME)
