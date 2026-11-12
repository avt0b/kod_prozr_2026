# Backend — «Код прозрачности»

FastAPI, Python 3.12, `uv`, SQLAlchemy 2 async + Postgres, Alembic. Модульный монолит по DDD.
Как устроены слои и модули, как добавить эндпоинт, правило риска или миграцию —
[docs/backend.md](../docs/backend.md). API и модель данных — [docs/contracts.md](../docs/contracts.md).

## Запуск на хосте

```sh
cp .env.example .env              # DATABASE_URL на localhost:5432, LLM выключена
uv sync
make migrate                      # alembic upgrade head
make seed-example                 # маленький пример из data/example (R01, R02, R07)
make run                          # http://localhost:8000/docs, /health
```

Полные сиды — `make seed` (читает `SEED_DIR`, по умолчанию `data/generated`). После загрузки
сиды сами анализируют обращения и пересчитывают риск: ручной `POST /risk/recompute` не нужен.

В Docker всё то же самое делает корневой `make up` / `make seed` (см. [docs/devops.md](../docs/devops.md)).

## Переменные окружения

| Переменная | По умолчанию | Что это |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://kodprozr:kodprozr@localhost:5432/kodprozr` | Postgres |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | через запятую |
| `LLM_BASE_URL` | пусто | OpenAI-совместимый endpoint. Пусто — LLM выключена, обращения разбираются правилами |
| `LLM_API_KEY`, `LLM_MODEL` | —, `qwen2.5:7b-instruct` | |
| `LLM_TIMEOUT_SECONDS` | `60` | таймаут запроса к LLM |
| `SEED_DIR` | `data/generated` | каталог JSON для `python -m src.seed` |
| `LOG_LEVEL`, `DB_ECHO`, `APP_ENV` | `INFO`, `false`, `dev` | |

## Команды

| Команда | Что делает |
| --- | --- |
| `make run` | uvicorn с автоперезагрузкой на :8000 |
| `make lint` | ruff + format --check + mypy --strict + import-linter |
| `make format` | ruff format |
| `make test-unit` | юнит-тесты, ничего не нужно |
| `make test-e2e` / `make test-integration` | нужен Postgres, см. ниже |
| `make test` | всё |
| `make migrate` / `make downgrade` / `make makemigrations m="..."` | Alembic |

## Тесты с Postgres

E2E и интеграционные тесты берут БД так: `TEST_DATABASE_URL`, если задан; при `CI=true` —
`DATABASE_URL`; иначе поднимают контейнер через testcontainers (`TEST_POSTGRES_IMAGE`, по
умолчанию `postgres:16-alpine`). Схема создаётся `Base.metadata.create_all`, таблицы
очищаются после каждого теста, поэтому БД должна быть отдельной, не рабочей.

```sh
docker run -d --name kodprozr-pg-test -e POSTGRES_USER=t -e POSTGRES_PASSWORD=t \
  -e POSTGRES_DB=t -p 55432:5432 postgres:16-alpine
TEST_DATABASE_URL=postgresql+asyncpg://t:t@localhost:55432/t make test
```

## Структура

```
src/
├── core/        # конфиг, ошибки (ProblemDetails), БД и Unit of Work, LLM-порт, логгер
├── modules/     # officials, counterparties, risk, appeals, reports, assistant, stats
├── web/         # composition root: create_app, сборка межмодульных ACL (wiring.py)
└── seed/        # python -m src.seed — загрузка сидов, анализ обращений, пересчёт риска
```

Модули не импортируют друг друга, домен не знает о фреймворках: это проверяет `uv run lint-imports`.


## Загрузка и аудит

`uv run python -m src.seed <каталог>` и `--dir <каталог>` эквивалентны. Нужны все 11 JSON-файлов
из `docs/data.md`, пустые сущности передаются как `[]`. `_truth/` игнорируется. Загрузчик
сначала проверяет формат, доменные ограничения, дубли и ссылки, затем в одной транзакции
заменяет данные, анализирует обращения и пересчитывает риск. При ошибке предыдущий набор
восстанавливается. Старые обращения, докладные и журнал очищаются при повторной загрузке.

Миграции `0002` и `0003` добавляют составной индекс контрактов и `core.audit_log`.
После обновления существующих данных вызовите `POST /risk/recompute`, чтобы контрактные
узлы evidence получили идентификаторы свёртки графа.

`GET /api/v1/audit?object_id=<uuid>&limit=20&offset=0` возвращает журнал `{items, total}`.
Создание обращения/докладной, просмотр профиля и пересчёт журналируются в транзакции операции;
для профиля доступны записи по person ID. Схемы тестов создаются отдельно от проверки миграций:
не запускайте Alembic и pytest одновременно на одной базе.

LLM использует общий HTTP-клиент на приложение с закрытием в lifespan, JSON проходит
валидацию схемой и одну повторную попытку. При недоступности модели разбор работает на правилах.
Шаблонная докладная включает полномочия, флаги/нормы, обращения и обязательную пометку;
LLM-переписывание (AI-09) ожидает проверки сохранения фактов и не включается автоматически.
