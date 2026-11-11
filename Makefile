.PHONY: help env up down build logs ps migrate seed test-back lint-back lint-front llm-up

.DEFAULT_GOAL := help

# Переменные из .env (если он есть) — нужен LLM_MODEL для llm-up.
-include .env

COMPOSE ?= docker compose
# Профиль llm подключаем в down/logs/ps, чтобы они видели и ollama.
COMPOSE_ALL := $(COMPOSE) --profile llm

LLM_MODEL ?= qwen2.5:7b-instruct

# --- Команды бэка и фронта --------------------------------------------------
# TODO(Кирилл): сверить с backend/README.md и frontend/package.json, когда каркасы будут готовы.
# Любую можно переопределить без правки файла: make seed SEED_CMD="python -m app.seed"

# Выполняются ВНУТРИ контейнера backend (venv образа в PATH, DATABASE_URL -> postgres:5432).
MIGRATE_CMD ?= alembic upgrade head
SEED_CMD ?= python -m src.seed

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

seed: env ## Залить синтетические данные (в контейнере backend)
	$(COMPOSE) run --rm backend sh -c "$(SEED_CMD)"

# --- Качество ---------------------------------------------------------------

test-back: ## Тесты бэка (uv, на хосте)
	cd backend && $(BACK_TEST_CMD)

lint-back: ## Линтер и формат бэка (ruff, на хосте)
	cd backend && $(BACK_LINT_CMD)

lint-front: ## Линтер фронта (на хосте)
	cd frontend && $(FRONT_LINT_CMD)

# --- Локальная LLM ----------------------------------------------------------

llm-up: env ## Поднять ollama и скачать модель LLM_MODEL
	$(COMPOSE_ALL) up -d --wait ollama
	$(COMPOSE_ALL) exec ollama ollama pull $(LLM_MODEL)
	@echo "Готово: в .env LLM_BASE_URL=http://ollama:11434/v1 LLM_MODEL=$(LLM_MODEL), затем make up"
