# Код прозрачности — рабочее место аналитика по профилактике коррупции

Веб-приложение для отдела по профилактике коррупционных правонарушений. Оно связывает данные о
служащих, их родственниках, компаниях и госконтрактах в граф, по прозрачным правилам находит
признаки конфликта интересов и выставляет балл риска с объяснением и ссылкой на норму закона.
Обращения граждан разбираются с помощью LLM: система определяет категорию и извлекает сущности,
а служащих, упомянутых в обращении, связывает с их профилями. Хакатон, ноябрь 2026.

## Структура

```
kod_prozr_2026/
├── backend/                 # FastAPI, Python 3.12, uv, alembic — см. backend/README.md
├── frontend/                # React + TypeScript + Vite — см. frontend/README.md
├── docs/                    # контракты, решения, DevOps
├── docker-compose.yml       # postgres, backend, frontend (+ ollama в профиле llm)
├── docker-compose.override.example.yml  # dev-режим: hot reload бэка, vite dev
├── Makefile                 # make help — все команды
├── .env.example             # переменные окружения
└── .github/workflows/ci.yml # ruff + pytest, eslint + build
```

## Начало работы разработчика

Сначала прочитайте [AGENTS.md](AGENTS.md) и [регламент команды](docs/workflow.md):
задача начинается с issue и ответственного, рабочие ветки создаются от `dev`, PR идут в `dev`,
релиз — `dev → main`. Для разделения работы между людьми есть **`/task-handoff`**:
[инструкция навыка](.agents/skills/task-handoff/SKILL.md).

## Быстрый старт

Нужны Docker с Compose v2.24+ и make.

```bash
cp .env.example .env && make up
```

- фронт: http://localhost:3000
- API: http://localhost:8000/api/v1, Swagger: http://localhost:8000/docs
- healthcheck: http://localhost:8000/health

Затем при необходимости загрузите демо-данные (`make seed`) и поднимите локальную LLM (`make llm-up`).
Остальные команды выводит `make help`.

## Документация

- [docs/workflow.md](docs/workflow.md) — issues, люди, метки, ветки, PR, релизы и `/task-handoff`
- [docs/contracts.md](docs/contracts.md) — общий контракт: порты, переменные, доменная модель, правила риска, API
- [docs/devops.md](docs/devops.md) — сервисы, dev-режим, локальная LLM, деплой на VPS
- [docs/variants.html](docs/variants.html) — варианты решения и выбранный подход
