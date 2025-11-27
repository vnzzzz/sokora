SHELL := /bin/bash

# Load .env when available so SERVICE_PORT and other env vars are reused.
ENV_FILE ?= .env
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
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
CONTAINER_NAME ?= sokora-app
DEV_CONTAINER_NAME ?= sokora-dev
SEED_DAYS_BACK ?= 60
SEED_DAYS_FORWARD ?= 60

.PHONY: help install run dev-shell seed test assets holiday-cache prepare-dev-assets build docker-build dev-build docker-run docker-stop

help:
	@printf "\nSokora make targets (devcontainer aware):\n"
	@printf "  make install         Install python deps via poetry and npm packages for builder\n"
	@printf "  make run             Run FastAPI (devcontainer) with reload on SERVICE_PORT (default: 8000)\n"
	@printf "  make dev-shell       Attach to the running devcontainer (name: %s)\n" "$(DEV_CONTAINER_NAME)"
	@printf "  make seed            Seed attendance data (vars: SEED_DAYS_BACK, SEED_DAYS_FORWARD)\n"
	@printf "  make test            Run cleanup + API/unit + e2e tests\n"
	@printf "  make assets          Build Tailwind CSS into assets/css/main.css\n"
	@printf "  make holiday-cache   Build holiday cache into assets/json/holidays_cache.json\n"
	@printf "  make build           Build production image (%s) from ./Dockerfile\n" "$(IMAGE_NAME)"
	@printf "  make dev-build       Build devcontainer image (%s) from .devcontainer/Dockerfile\n" "$(DEV_IMAGE_NAME)"
	@printf "  make docker-build    Build production image (%s) using VERSION tag from .env\n" "$(VERSION_TAG)"
	@printf "  make docker-run      Run production container (tag: %s) with port mapping and data volume mount\n" "$(VERSION_TAG)"
	@printf "  make docker-stop     Stop and remove the production container\n\n"

install:
	poetry install --no-root
	cd builder && npm install

run: prepare-dev-assets
	poetry run uvicorn app.main:app --host 0.0.0.0 --port $(SERVICE_PORT) --reload

dev-shell:
	docker exec -it $(DEV_CONTAINER_NAME) bash

seed:
	mkdir -p data
	./scripts/seeding/run_seeder.sh $(SEED_DAYS_BACK) $(SEED_DAYS_FORWARD)

test:
	./scripts/testing/run_test.sh

assets:
	mkdir -p assets/css assets/js assets/json
	cd builder && npm install
	cd builder && npx tailwindcss -i input.css -o ../assets/css/main.css --minify

prepare-dev-assets:
	./scripts/prepare_dev_assets.sh

holiday-cache:
	mkdir -p assets/json
	poetry run python scripts/build_holiday_cache.py

build:
	docker build -t $(IMAGE_NAME) .

docker-build:
	docker build -t $(VERSION_TAG) .

dev-build:
	docker build -f .devcontainer/Dockerfile -t $(DEV_IMAGE_NAME) ..

docker-run:
	docker run -d --name $(CONTAINER_NAME) --env-file $(ENV_FILE) \
		-p $(SERVICE_PORT):8000 \
		-v $(PWD)/data:/app/data \
		$(VERSION_TAG)

docker-stop:
	-docker stop $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)
