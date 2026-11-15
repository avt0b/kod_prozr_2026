.PHONY: help env up down build logs ps migrate seed reset data data-check precompute eval \
	smoke test-back test-data lint-back lint-front llm-up llm-check \
	dump restore offline-bundle offline-load video

.DEFAULT_GOAL := help
# bash: pipefail в dump/restore/video.
SHELL := /bin/bash

# Переменные из .env (если он есть): LLM_MODEL, порты, образы, POSTGRES_*.
-include .env

COMPOSE ?= docker compose
# Профиль llm подключаем в down/logs/ps, чтобы они видели и ollama.
COMPOSE_ALL := $(COMPOSE) --profile llm

LLM_MODEL ?= qwen2.5:7b-instruct

# Хост-порты (contracts.md); если порт занят — переопределить в .env, VITE_API_URL — тоже.
POSTGRES_PORT ?= 5432
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000
PG_USER := $(or $(POSTGRES_USER),kodprozr)
PG_DB := $(or $(POSTGRES_DB),kodprozr)

# Сборка в сети хоста: bridge-сеть Docker на машинах команды не выходит в интернет
# (VPN/TUN), и npm ci / uv sync висят. Compose 2.3x+ собирает через bake, а bake требует
# явного разрешения network.host — поэтому сборка идёт через `docker buildx bake`.
# Обычная сборка в bridge: make build BUILD_NETWORK=default.
BUILD_NETWORK ?= host

# Офлайн-режим (резервный ноутбук): без сборки и без обращений к registry.
#   make reset OFFLINE=1, make llm-up OFFLINE=1 — после make offline-load.
OFFLINE ?= 0
ifeq ($(OFFLINE),1)
BUILD_DEP :=
UP_FLAGS := --no-build --pull never
else
BUILD_DEP := build
UP_FLAGS := --no-build
endif

# GPU для Ollama: auto — если в `docker info` есть runtime nvidia; 1 — принудительно; 0 — CPU.
LLM_GPU ?= auto
llm_gpu = $(if $(filter auto,$(LLM_GPU)),$(shell docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q nvidia && echo 1 || echo 0),$(LLM_GPU))
COMPOSE_LLM = $(COMPOSE_ALL) $(if $(filter 1,$(llm_gpu)),-f docker-compose.yml -f docker-compose.gpu.yml)

# Артефакты (dist/ в .gitignore).
DB_DIR ?= dist/db
VIDEO_DIR ?= dist/video
OFFLINE_DIR ?= dist/offline
VIDEO_SPEC ?= e2e/demo.spec.ts

# --- Команды бэка и фронта --------------------------------------------------
# Любую можно переопределить без правки файла: make seed SEED_CMD="python -m src.seed --dir ..."

# Выполняются ВНУТРИ контейнера backend (venv образа в PATH, DATABASE_URL -> postgres:5432).
MIGRATE_CMD ?= alembic upgrade head
# data/generated монтируется в /app/data/generated (docker-compose.yml): сиды с предрасчётом.
SEED_CMD ?= python -m src.seed --dir data/generated

PYTHON ?= python3
API_URL ?= http://localhost:$(BACKEND_PORT)
FRONT_URL ?= http://localhost:$(FRONTEND_PORT)
DATA_DIR ?= data/generated
# Хост-команды бэка ходят в Postgres из compose на localhost.
HOST_DB ?= postgresql+asyncpg://$(PG_USER):$(or $(POSTGRES_PASSWORD),kodprozr)@localhost:$(POSTGRES_PORT)/$(PG_DB)
DEMO_APPEALS = $$($(PYTHON) -c "import json;print(' '.join(json.load(open('$(CURDIR)/$(DATA_DIR)/_truth/meta.json'))['demo_appeal_ids']))")

# Выполняются НА ХОСТЕ в backend/ через uv (dev-зависимости в образ не попадают).
UV ?= uv run
BACK_TEST_CMD ?= $(UV) pytest
BACK_LINT_CMD ?= $(UV) ruff check . && $(UV) ruff format --check . && $(UV) mypy src tests && $(UV) lint-imports

# Выполняется на хосте в frontend/ (нужен npm ci).
FRONT_LINT_CMD ?= npm run lint

# --- Стек в Docker ----------------------------------------------------------

help: ## Показать список команд
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  make %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Создать .env из .env.example (существующий не трогает)
	@test -f .env || (cp .env.example .env && echo "Создан .env из .env.example")

up: env $(BUILD_DEP) ## Собрать и поднять весь стек в фоне (OFFLINE=1 — без сборки и сети)
	$(COMPOSE) up -d $(UP_FLAGS)
	@echo "frontend: $(FRONT_URL)  backend: $(API_URL)/docs  health: $(API_URL)/health"

down: ## Остановить стек вместе с ollama (данные в томах сохраняются)
	$(COMPOSE_ALL) down

build: env ## Пересобрать образы (в сети хоста; BUILD_NETWORK=default — в bridge)
ifeq ($(BUILD_NETWORK),host)
	@set -o pipefail; BUILD_NETWORK=host $(COMPOSE) build --print 2>/dev/null \
		| docker buildx bake --allow=network.host -f - || { $(COMPOSE) config -q; exit 1; }
else
	BUILD_NETWORK=$(BUILD_NETWORK) $(COMPOSE) build
endif

logs: ## Логи; один сервис: make logs s=backend
	$(COMPOSE_ALL) logs -f --tail=200 $(s)

ps: ## Состояние контейнеров
	$(COMPOSE_ALL) ps

# --- Данные -----------------------------------------------------------------

migrate: env ## Применить миграции БД (в контейнере backend)
	$(COMPOSE) run --rm backend sh -c "$(MIGRATE_CMD)"

seed: env ## Залить синтетику с предрасчётом и пересчитать риск (в контейнере backend)
	$(COMPOSE) run --rm backend sh -c "$(SEED_CMD)"

# Без --profile llm: down -v снёс бы и том ollama_models со скачанной моделью,
# а работающую ollama reset не трогает (модель остаётся прогретой).
reset: env $(BUILD_DEP) ## Снести БД, поднять стек, миграции и сиды — «как перед демо»
	$(COMPOSE) down --volumes --remove-orphans
	$(COMPOSE) up -d $(UP_FLAGS) --wait
	$(MAKE) seed
	@echo "Стенд готов: $(FRONT_URL)"

dump: ## Дамп БД стенда в dist/db/kodprozr-<дата>.sql.gz
	@mkdir -p $(DB_DIR)
	@set -o pipefail; f=$(DB_DIR)/kodprozr-$$(date +%Y%m%d-%H%M%S).sql.gz; \
	$(COMPOSE) exec -T postgres pg_dump -U $(PG_USER) -d $(PG_DB) --no-owner --no-privileges \
		| gzip >"$$f.part" && mv "$$f.part" "$$f" || { rm -f "$$f.part"; exit 1; }; \
	echo "Дамп: $$f ($$(du -h "$$f" | cut -f1))"

restore: env ## Восстановить БД из дампа: make restore FILE=dist/db/kodprozr-....sql.gz
	@test -n "$(FILE)" || { echo "Укажите дамп: make restore FILE=$(DB_DIR)/kodprozr-<дата>.sql.gz"; exit 1; }
	@test -f "$(FILE)" || { echo "Нет файла $(FILE)"; exit 1; }
	$(COMPOSE) up -d $(UP_FLAGS) --wait postgres
	$(COMPOSE) stop backend frontend
	$(COMPOSE) exec -T postgres dropdb -U $(PG_USER) --if-exists --force $(PG_DB)
	$(COMPOSE) exec -T postgres createdb -U $(PG_USER) $(PG_DB)
	@set -o pipefail; gunzip -c "$(FILE)" \
		| $(COMPOSE) exec -T postgres psql -U $(PG_USER) -d $(PG_DB) -v ON_ERROR_STOP=1 -q -o /dev/null
	$(COMPOSE) up -d $(UP_FLAGS) --wait
	@echo "БД восстановлена из $(FILE): $(FRONT_URL)"

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

# --- Демо: резервный ноутбук и видео ----------------------------------------

offline-bundle: env ## Офлайн-пакет в dist/offline/: образы, модель, .env, исходники, дамп
	OFFLINE_DIR=$(OFFLINE_DIR) POSTGRES_IMAGE=$(POSTGRES_IMAGE) OLLAMA_IMAGE=$(OLLAMA_IMAGE) \
		scripts/offline.sh bundle

offline-load: ## Загрузить офлайн-пакет (OFFLINE_DIR=...), затем make reset OFFLINE=1
	OFFLINE_DIR=$(OFFLINE_DIR) POSTGRES_IMAGE=$(POSTGRES_IMAGE) OLLAMA_IMAGE=$(OLLAMA_IMAGE) \
		scripts/offline.sh load

video: ## Видео-бэкап: Playwright-сценарий демо против стенда, видео в dist/video/
	@test -f frontend/$(VIDEO_SPEC) || { echo "Нет frontend/$(VIDEO_SPEC): Playwright-сценарий демо ещё не влит (зона фронта)."; exit 1; }
	@test -d frontend/node_modules/@playwright/test || { echo "Нет Playwright: cd frontend && npm ci && npx playwright install chromium"; exit 1; }
	@curl -fsS -m 5 -o /dev/null $(FRONT_URL) || { echo "Стенд не отвечает на $(FRONT_URL): сначала make reset"; exit 1; }
	@stamp=$$(mktemp); \
	(cd frontend && DEMO_VIDEO=1 BASE_URL=$(FRONT_URL) npx playwright test $(VIDEO_SPEC)); rc=$$?; \
	mkdir -p $(VIDEO_DIR); ts=$$(date +%Y%m%d-%H%M%S); n=0; \
	while IFS= read -r v; do n=$$((n+1)); cp "$$v" "$(VIDEO_DIR)/demo-$$ts-$$n.$${v##*.}"; done \
		< <(find frontend -path frontend/node_modules -prune -o -type f \( -name '*.webm' -o -name '*.mp4' \) -newer "$$stamp" -print); \
	rm -f "$$stamp"; \
	[ $$n -gt 0 ] || { echo "Сценарий не записал видео: проверьте, что при DEMO_VIDEO=1 включена запись (video: 'on')."; exit 1; }; \
	ls -lh $(VIDEO_DIR)/demo-$$ts-*; \
	[ $$rc -eq 0 ] || echo "ВНИМАНИЕ: сценарий упал (код $$rc), видео сохранено частично."; \
	exit $$rc

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

llm-up: env ## Поднять ollama (GPU, если есть runtime nvidia), скачать и прогреть LLM_MODEL
	@echo "Ollama: $(if $(filter 1,$(llm_gpu)),NVIDIA GPU (docker-compose.gpu.yml),CPU — runtime nvidia не найден; LLM_GPU=1 — принудительно)"
	$(COMPOSE_LLM) up -d $(UP_FLAGS) --wait ollama
	$(COMPOSE_LLM) exec ollama sh -c 'ollama show $(LLM_MODEL) >/dev/null 2>&1 || ollama pull $(LLM_MODEL)'
	$(COMPOSE_LLM) exec ollama ollama run $(LLM_MODEL) "Ответь: ok" >/dev/null
	@echo "Готово: в .env LLM_BASE_URL=http://ollama:11434/v1 LLM_MODEL=$(LLM_MODEL), затем make up"

llm-check: ## Проверить, что бэк в Docker видит LLM_BASE_URL (GET /models)
	@$(COMPOSE) exec -T backend python -c "import os, urllib.request as u; b=os.environ.get('LLM_BASE_URL', ''); \
	print('LLM_BASE_URL пуст: фоллбэк без LLM') if not b else print(b, '->', u.urlopen(b.rstrip('/') + '/models', timeout=5).read()[:300].decode())"
