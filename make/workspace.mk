SEED_DAYS_BACK ?= 60
SEED_DAYS_FORWARD ?= 60

.PHONY: help sync install run seed test assets prepare-dev-assets holiday-cache migrate lint format format-check typecheck quality

help:
	@printf "\nSokora workspace targets:\n"
	@printf "  make sync            Sync Python dependencies from uv.lock\n"
	@printf "  make install         Sync Python deps and npm packages for builder\n"
	@printf "  make run             Run FastAPI with reload on SERVICE_PORT (default: 8000)\n"
	@printf "  make seed            Seed attendance data (vars: SEED_DAYS_BACK, SEED_DAYS_FORWARD)\n"
	@printf "  make test            Run cleanup + API/unit + e2e tests\n"
	@printf "  make assets          Build CSS/JS into assets/ via builder\n"
	@printf "  make holiday-cache   Build holiday cache into assets/json/holidays_cache.json\n"
	@printf "  make migrate         Run Alembic migrations (upgrade head)\n"
	@printf "  make lint            Run Ruff lint and import checks\n"
	@printf "  make format          Apply Ruff import sorting and formatting\n"
	@printf "  make format-check    Check Ruff formatting without modifying files\n"
	@printf "  make typecheck       Run mypy\n"
	@printf "  make quality         Run lint + format-check + typecheck\n\n"

sync:
	uv sync --locked

install: sync
	./scripts/build_assets.sh

run: prepare-dev-assets
	uv run uvicorn app.main:app --host 0.0.0.0 --port $(SERVICE_PORT) --reload

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
	PYTHONPATH=$(CURDIR) uv run alembic -c scripts/migration/alembic.ini upgrade head

lint: sync
	uv run ruff check app scripts

format: sync
	uv run ruff check app scripts --select I --fix
	uv run ruff format app scripts

format-check: sync
	uv run ruff format --check app scripts

typecheck: sync
	uv run mypy app

quality: lint format-check typecheck
