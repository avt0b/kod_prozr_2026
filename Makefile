.PHONY: help env up down build logs ps migrate seed reset data data-check precompute eval \
	smoke test-back test-data lint-back lint-front llm-up

.DEFAULT_GOAL := help

# Переменные из .env (если он есть) — нужен LLM_MODEL для llm-up.
-include .env

COMPOSE ?= docker compose
# Профиль llm подключаем в down/logs/ps, чтобы они видели и ollama.
COMPOSE_ALL := $(COMPOSE) --profile llm

LLM_MODEL ?= qwen2.5:7b-instruct

# --- Команды бэка и фронта --------------------------------------------------
# Любую можно переопределить без правки файла: make seed SEED_CMD="python -m src.seed --dir ..."

# Выполняются ВНУТРИ контейнера backend (venv образа в PATH, DATABASE_URL -> postgres:5432).
MIGRATE_CMD ?= alembic upgrade head
# data/generated монтируется в /app/data/generated (docker-compose.yml): сиды с предрасчётом.
SEED_CMD ?= python -m src.seed --dir data/generated

PYTHON ?= python3
API_URL ?= http://localhost:8000
DATA_DIR ?= data/generated
# Хост-команды бэка ходят в Postgres из compose на localhost.
HOST_DB ?= postgresql+asyncpg://$(or $(POSTGRES_USER),kodprozr):$(or $(POSTGRES_PASSWORD),kodprozr)@localhost:5432/$(or $(POSTGRES_DB),kodprozr)
DEMO_APPEALS = $$($(PYTHON) -c "import json;print(' '.join(json.load(open('$(CURDIR)/$(DATA_DIR)/_truth/meta.json'))['demo_appeal_ids']))")

# Выполняются НА ХОСТЕ в backend/ через uv (dev-зависимости в образ не попадают).
UV ?= uv run
BACK_TEST_CMD ?= $(UV) pytest
BACK_LINT_CMD ?= $(UV) ruff check . && $(UV) ruff format --check . && $(UV) mypy src tests && $(UV) lint-imports

# Выполняется на хосте в frontend/ (нужен npm ci).
FRONT_LINT_CMD ?= npm run lint

# --- Стек в Docker ----------------------------------------------------------

help: ## Показать список команд
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  make %-11s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Создать .env из .env.example (существующий не трогает)
	@test -f .env || (cp .env.example .env && echo "Создан .env из .env.example")

up: env ## Собрать и поднять весь стек в фоне
	$(COMPOSE) up -d --build
	@echo "frontend: http://localhost:3000  backend: http://localhost:8000/docs  health: http://localhost:8000/health"

down: ## Остановить стек (данные в томах сохраняются)
	$(COMPOSE_ALL) down

build: ## Пересобрать образы
	$(COMPOSE) build

logs: ## Логи; один сервис: make logs s=backend
	$(COMPOSE_ALL) logs -f --tail=200 $(s)

ps: ## Состояние контейнеров
	$(COMPOSE_ALL) ps

# --- Данные -----------------------------------------------------------------

migrate: env ## Применить миграции БД (в контейнере backend)
	$(COMPOSE) run --rm backend sh -c "$(MIGRATE_CMD)"

seed: env ## Залить синтетику с предрасчётом и пересчитать риск (в контейнере backend)
	$(COMPOSE) run --rm backend sh -c "$(SEED_CMD)"

reset: env ## Снести тома, поднять стек, миграции и сиды — «как перед демо»
	$(COMPOSE_ALL) down --volumes --remove-orphans
	$(COMPOSE) up -d --build --wait
	$(MAKE) seed
	@echo "Стенд готов: http://localhost:3000"

data: ## Пересоздать синтетику (seed 42); затем make precompute
	$(PYTHON) -m data.generator --seed 42 --out $(DATA_DIR)

data-check: ## Проверить сгенерированные данные (data.md §7)
	$(PYTHON) -m data.generator.check $(DATA_DIR)
	$(PYTHON) -m data.generator.check $(DATA_DIR)/sample --partial

precompute: ## Предрасчёт анализа обращений в сиды (AI-06; LLM — из backend/.env)
	cd backend && DATABASE_URL=$(HOST_DB) $(UV) python -m src.seed.precompute \
		--dir $(CURDIR)/$(DATA_DIR) --keep-new $(DEMO_APPEALS)

eval: ## Метрики качества после make seed; с LLM: make eval EVAL_ARGS="--llm --limit 30"
	cd backend && DATABASE_URL=$(HOST_DB) $(UV) python -m src.eval --dir $(CURDIR)/$(DATA_DIR) \
		--out $(CURDIR)/eval/report.json $(EVAL_ARGS)

smoke: ## Smoke всех эндпоинтов + демо-обращение (меняет данные: потом make reset)
	$(PYTHON) scripts/smoke.py --api $(API_URL)

# --- Качество ---------------------------------------------------------------

test-back: ## Тесты бэка (uv, на хосте)
	cd backend && $(BACK_TEST_CMD)

test-data: ## Тесты генератора синтетики
	$(PYTHON) -m unittest discover -s data/tests -t .

lint-back: ## Линтер и формат бэка (ruff, на хосте)
	cd backend && $(BACK_LINT_CMD)

lint-front: ## Линтер фронта (на хосте)
	cd frontend && $(FRONT_LINT_CMD)

# --- Локальная LLM ----------------------------------------------------------

llm-up: env ## Поднять ollama, скачать и прогреть модель LLM_MODEL
	$(COMPOSE_ALL) up -d --wait ollama
	$(COMPOSE_ALL) exec ollama ollama pull $(LLM_MODEL)
	$(COMPOSE_ALL) exec ollama ollama run $(LLM_MODEL) "Ответь: ok" >/dev/null
	@echo "Готово: в .env LLM_BASE_URL=http://ollama:11434/v1 LLM_MODEL=$(LLM_MODEL), затем make up"
