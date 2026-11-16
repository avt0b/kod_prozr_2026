.PHONY: run test test-unit test-integration test-e2e lint lint-fix format check migrate downgrade makemigrations migration-heads seed seed-example

run: ## API на :8000 с автоперезагрузкой
	uv run uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

test: ## Все тесты
	uv run pytest -v

test-unit: ## Юнит-тесты: без БД и сети
	uv run pytest tests/unit -v

test-integration: ## Интеграционные: нужен Postgres (TEST_DATABASE_URL или Docker)
	uv run pytest tests/integration -v

test-e2e: ## E2E через HTTP: нужен Postgres (TEST_DATABASE_URL или Docker)
	uv run pytest tests/e2e -v

lint: ## ruff + ruff format --check + mypy --strict + границы модулей
	uv run ruff check src tests migrations
	uv run ruff format --check src tests migrations
	uv run mypy src tests
	uv run lint-imports

lint-fix:
	uv run ruff check --fix src tests migrations

format:
	uv run ruff format src tests migrations

check:
	uv run ruff format --check src tests migrations

migrate:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade -1

makemigrations: ## make makemigrations m="add something"
	uv run alembic revision --autogenerate -m "$(m)"

migration-heads:
	uv run alembic heads

seed: ## Сиды из SEED_DIR (по умолчанию data/generated)
	uv run python -m src.seed

seed-example: ## Маленький пример из data/example (R01, R02, R07)
	uv run python -m src.seed --dir data/example
