# Бэкенд

Руководство для тех, кто пишет `backend/`: как устроен эталон, что из него берём, куда класть код и
как добавлять модули, эндпоинты, правила риска и миграции. Модель данных, правила R01–R08 и API
описаны в [contracts.md](contracts.md), решения — в [decisions.md](decisions.md) (ADR-03, 04, 05, 08,
09, 10), ИИ-часть — в [ai.md](ai.md).

Пути эталона ниже даны от `~/Projects/backend/`. Эталон — сервис `optimus` (FastAPI, DDD по Эвансу).
Соседний `nexus` (Elixir) к нам отношения не имеет.

---

Процесс задач, веток и PR — [workflow.md](workflow.md); рабочие PR направляются в `dev`.

## 1. Эталон: что читать и что берём

### Что прочитать в первый день (около часа)

1. `.agents/optimus/architecture.md` — модули, четыре слоя, агрегаты, порты и ACL, composition root,
   import-linter.
2. `.agents/optimus/conventions.md` — типы, Pydantic и dataclass по слоям, имена, логи, конфиг.
3. `.agents/optimus/data-and-migrations.md` — Unit of Work, репозитории, Alembic.
4. `.agents/optimus/testing.md` — три уровня тестов, что мокать и что нет.
5. Маленький модуль целиком: `optimus/src/modules/waitlist/` (около 15 файлов). На нём видна вся
   цепочка: роутер → DI → use case → порт → репозиторий → ORM-модель.

Модуль `optimus/src/modules/training/` большой. Его читаем выборочно, по файлам из таблицы ниже.

### Что берём

| Что | Пример в эталоне |
| --- | --- |
| Модульный монолит: модуль = bounded context, своя схема Postgres | `optimus/src/modules/*`, `optimus/README.md` |
| Слои `domain / application / infrastructure / presentation` | любой модуль, проще всего `waitlist` |
| Агрегат: приватное состояние, поведение методами, инварианты внутри | `training/domain/workout_report.py`, `training/domain/workout.py` |
| Value Object — `@dataclass(frozen=True)` с проверкой в `__post_init__` | `training/domain/value_objects.py` |
| Доменная политика (правило без естественного владельца) | `training/domain/workout_access_policy.py` |
| Доменные исключения, наследники `DomainError` | `training/domain/exceptions.py`, `core/exceptions/base.py` |
| Use case: класс `<Действие>UseCase` с одним методом `execute` | `training/application/use_cases/*.py` |
| Порт — `Protocol` в `application/interfaces/` | `training/application/interfaces/workout_repository.py` |
| Репозиторий маппит ORM ↔ домен (`to_entity` / `from_entity`) | `waitlist/infrastructure/database/models/waitlist_entry.py` |
| Unit of Work: транзакцией владеет use case | `core/infrastructure/database/unit_of_work.py`, `training/application/use_cases/apply_parsed_fit.py` |
| DI модуля в `presentation/dependencies.py` | `waitlist/presentation/dependencies.py` |
| Порт + ACL-адаптер для межмодульного вызова | `training/domain/mentorship_checker.py` → `training/infrastructure/adapters/mentorship_acl.py` → `web/dependencies.py` |
| Composition root: роутеры, обработчики ошибок, связка модулей | `optimus/src/web/create_app.py`, `optimus/src/web/dependencies.py` |
| Заглушка-зависимость, которую подменяет `web` | `get_relationship_checker` в `training/presentation/dependencies.py` |
| Ошибки в формате ProblemDetails (RFC 7807) | `core/schemas/problem_details.py`, `core/infrastructure/exception_handler.py` |
| Конфиг на `pydantic-settings`, секреты как `SecretStr` | `core/config.py` |
| Логгер `loguru` через `get_logger` | `core/infrastructure/logger.py` |
| `SafeString` для пользовательского текста | `core/schemas/types.py` |
| База, миксины, движок, сессия | `core/infrastructure/database/{base,mixins,database}.py` |
| Alembic: async, `include_schemas`, все модели импортированы в `env.py` | `optimus/migrations/env.py`, `optimus/alembic.ini` |
| Границы слоёв и модулей проверяет `import-linter` | `[tool.importlinter]` в `optimus/pyproject.toml` |
| Тесты unit / integration / e2e, testcontainers локально и сервисы в CI | `optimus/tests/*/conftest.py` |
| Makefile-цели `lint`, `test-unit`, `migrate`, `makemigrations` | `optimus/Makefile` |
| Многостадийный Dockerfile на `uv` | `optimus/Dockerfile` |

### Что не берём

- NATS, FastStream, шардирование сабджектов (`core/infrastructure/messaging/`). У нас один процесс
  и нет брокера.
- S3 и `aioboto3`: файлов у нас нет.
- JWT, `core/access` (права и политики на строки). В контракте нет аутентификации.
- Модуль `projector` как отдельный read-side. Идею берём частично: чтения «для экрана» собираются
  через порты (раздел 6).

### Что в эталоне не повторяем

В эталоне есть переходный код. В нашем проекте его не копируем:

- Репозиторий сам делает `commit()` (`waitlist_repository.py`, метод `commit` в
  `WorkoutRepositoryInterface`), есть `commit_outside_unit_of_work`. У нас коммитит только Unit of
  Work в use case.
- Роутер после use case читает репозиторий напрямую (`create_workout_report` в
  `training_router.py`). У нас use case возвращает DTO, и роутер репозиториев не видит.
- Отдельная функция-обработчик на каждое исключение (`training/infrastructure/exception_handler.py`,
  около 390 строк) и `# mypy: ignore-errors` в этих файлах. У нас обработчики регистрируются на
  базовые классы ошибок в `core` (раздел 5).
- f-строки и `%s` в логах (`training/infrastructure/adapters/event_bus.py`, `web/create_app.py`).
  Пишем только `logger.info("... {}", x)`.
- `get_all()` без лимита. Любой список у нас с `limit`.
- `src/core/__init__.py` реэкспортирует всё ядро, включая SQLAlchemy. У нас `__init__.py` в `core`
  пустые, импорт идёт из конкретного файла, иначе import-linter видит косвенные зависимости домена
  от инфраструктуры.

---

## 2. Стек и инструменты

Как в эталоне, кроме отмеченного.

| Что | Чем | Примечание |
| --- | --- | --- |
| Python | 3.12 | `backend/.python-version`, `requires-python = ">=3.12"` |
| Зависимости | **только `uv`** | `pyproject.toml` + `uv.lock`, lock коммитим. `pip`, `poetry`, `requirements.txt` не используем |
| Веб | FastAPI, uvicorn | приложение — `src.web.main:app` (на это рассчитаны compose и `.env.example`) |
| Валидация | Pydantic v2, `pydantic-settings` | Pydantic только в `presentation`, в `infrastructure` и в конфиге |
| БД | PostgreSQL 16, SQLAlchemy 2.0 async + `asyncpg` | версия БД как в `docker-compose.yml` и CI |
| Миграции | Alembic (async `env.py`) | хук `ruff format` на новые файлы, как в `optimus/alembic.ini` |
| HTTP-клиент | `httpx` | только адаптер LLM |
| Логи | `loguru` | через `src/core/infrastructure/logger.py` |
| Санитизация | `nh3` | тип `SafeString` |
| ИИ и ML | `scikit-learn`, `numpy`, `pymorphy3`, `rapidfuzz`, `jinja2` | **наше**: R08, сопоставление ФИО, шаблон докладной |
| Линт и формат | `ruff` | `line-length = 100`, `target-version = "py312"`, правила `E, F, I, UP` + `PLC0415` (импорт только на уровне модуля) |
| Типы | `mypy --strict` | `[tool.mypy] strict = true` |
| Границы | `import-linter` (`lint-imports`) | контракты в `pyproject.toml`, раздел 3 |
| Тесты | `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`), `pytest-mock`, `testcontainers[postgres]`, `freezegun` | `@pytest.mark.asyncio` не пишем |

Цели `backend/Makefile` (имена как в `optimus/Makefile`):

| Цель | Команда |
| --- | --- |
| `run` | `uv run uvicorn src.web.main:app --reload --port 8000` |
| `lint` | `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src tests && uv run lint-imports` |
| `format` | `uv run ruff format src tests` |
| `test-unit` / `test-integration` / `test-e2e` | `uv run pytest tests/unit` / `tests/integration` / `tests/e2e` |
| `test` | `uv run pytest` |
| `migrate` / `downgrade` | `uv run alembic upgrade head` / `uv run alembic downgrade -1` |
| `makemigrations` | `uv run alembic revision --autogenerate -m "$(m)"` |
| `seed` | `uv run python -m src.seed` |

Корневой `Makefile` вызывает `make test-back` и `make lint-back`. CI сейчас гоняет только `ruff` и
`pytest`, поэтому `mypy` и `lint-imports` в `BACK_LINT_CMD` и в `.github/workflows/ci.yml` нужно
добавить (с Кириллом).

---

## 3. Слои модуля и границы

### Раскладка модуля

```
src/modules/<module>/
├── domain/                     # чистый Python: ни FastAPI, ни SQLAlchemy, ни Pydantic, ни httpx
│   ├── <aggregate>.py          # агрегат: appeal.py, risk_flag.py
│   ├── value_objects.py        # frozen dataclass
│   ├── enums.py                # StrEnum; значения уходят в API, переименование ломает контракт
│   ├── exceptions.py           # наследники ошибок из src.core.exceptions
│   └── *_policy.py             # доменные правила и сервисы: routing_policy.py, scoring.py
├── application/
│   ├── dto/                    # @dataclass: вход и выход use case
│   ├── interfaces/             # Protocol-порты: репозитории, источники из чужих модулей, ИИ
│   └── use_cases/<action>.py   # <Action>UseCase.execute(...)
├── infrastructure/
│   ├── database/
│   │   ├── schema.py           # <MODULE>_SCHEMA = "<module>"
│   │   └── models/             # ORM-модели с to_entity()/from_entity()
│   ├── repositories/           # реализации портов-репозиториев
│   └── adapters/               # <чужой>_acl.py, адаптеры ИИ/ML
└── presentation/
    ├── api/<module>_router.py  # тонкие роутеры
    ├── schemas/                # Pydantic request/response
    └── dependencies.py         # DI модуля + заглушки чужих портов
```

| Слой | Что лежит | Что запрещено |
| --- | --- | --- |
| `domain` | агрегаты, VO, enum, доменные исключения, политики, правила риска, формулы | любой импорт инфраструктуры и фреймворков, БД, сеть |
| `application` | use cases, DTO (`@dataclass`), порты (`Protocol`), оркестрация, Unit of Work | импорт `infrastructure` своего и чужих модулей |
| `infrastructure` | репозитории, ORM-модели, ACL-адаптеры, адаптеры LLM и ML, Pydantic-схемы ответов LLM | бизнес-правила, знание о `presentation` |
| `presentation` | роутеры, Pydantic-схемы API, `dependencies.py` | бизнес-логика: `if` с правилом предметной области в роутере — ошибка |

Правила, общие для всех модулей:

- **Роутер**: провалидировать вход схемой, собрать DTO, вызвать use case, вернуть ответ. Пример тонкого
  роутера — `waitlist/presentation/api/waitlist_router.py`.
- **Use case** получает зависимости через конструктор по интерфейсам, возвращает DTO или `None`.
  Агрегат наружу не отдаёт. Ожидаемая ошибка — доменное исключение, а не `None` и не флаг.
- **Репозиторий** — один на корень агрегата. Принимает и возвращает доменные объекты, ORM-модели
  наружу не выходят. Списки всегда с `limit` (жёсткий потолок 100).
- **Транзакция**: одна транзакция меняет один агрегат. Публикация и вызовы чужих модулей идут после
  коммита.
- **Данные по слоям**: Pydantic в `presentation`, `@dataclass` в `application`,
  `@dataclass(frozen=True)` и обычные классы в `domain`.
- `presentation/dependencies.py` — единственное место модуля, где одновременно видны `application` и
  `infrastructure`. Здесь конкретные классы собираются в use case.

### Направление зависимостей

```
presentation ──▶ application ──▶ domain ◀── infrastructure
      └─────────────(DI)──────────────────────▶ infrastructure
```

### Между модулями

**Прямой импорт чужого модуля запрещён на любом слое.** Чужие таблицы не читаем даже на чтение.
Внешних ключей между схемами разных модулей нет: чужой id хранится как UUID без FK
(`CompanyRole.person_id`, `Appeal.linked_person_ids`).

Узнать что-то у чужого модуля можно одним способом — **порт + ACL-адаптер**, как
`training → mentorship` в эталоне:

1. Модуль-потребитель объявляет порт в своих терминах:
   `risk/application/interfaces/officials_source.py`.
2. ACL-адаптер в потребителе переводит чужую модель в свою и чужой модуль не импортирует. Он
   объявляет локальный `Protocol` того, что ему нужно снаружи:
   `risk/infrastructure/adapters/officials_acl.py`.
3. Модуль-источник отдаёт данные через свой use case (`officials/application/use_cases/get_officials_snapshot.py`).
4. `src/web/dependencies.py` — единственное место, которое знает оба модуля. Здесь собирается
   `OfficialsACLAdapter(GetOfficialsSnapshotUseCase(...))`. В `create_app.py` заглушка потребителя
   подменяется через `app.dependency_overrides`.

Межмодульные события через брокер, как в эталоне, нам не нужны. Единственная межмодульная реакция —
пересчёт риска после обращения (ADR-10). Она синхронная, поэтому тоже идёт через порт.

### Как это проверяется: import-linter

Контракты лежат в `backend/pyproject.toml`, проверка — `uv run lint-imports` (входит в `make lint`).
У эталона по три контракта на модуль. У нас та же логика, записанная короче, через `containers` и
`independence`:

```toml
[tool.importlinter]
root_package = "src"
include_external_packages = true

[[tool.importlinter.contracts]]
name = "Слои внутри каждого модуля"
type = "layers"
containers = [
  "src.modules.officials", "src.modules.counterparties", "src.modules.risk",
  "src.modules.appeals", "src.modules.reports", "src.modules.assistant",
]
layers = ["presentation", "application", "domain"]

[[tool.importlinter.contracts]]
name = "Модули не импортируют друг друга"
type = "independence"
modules = [
  "src.modules.officials", "src.modules.counterparties", "src.modules.risk",
  "src.modules.appeals", "src.modules.reports", "src.modules.assistant",
]

[[tool.importlinter.contracts]]
name = "domain и application не знают об инфраструктуре"
type = "forbidden"
source_modules = [
  "src.modules.officials.domain", "src.modules.officials.application",
  # ... domain и application каждого модуля
]
forbidden_modules = [
  "src.modules.officials.infrastructure",
  # ... infrastructure каждого модуля
  "src.core.infrastructure.database",
  "src.core.infrastructure.llm",
  "src.core.infrastructure.dependencies",
  "src.core.infrastructure.exception_handler",
]

[[tool.importlinter.contracts]]
name = "domain — чистый Python"
type = "forbidden"
source_modules = ["src.modules.officials.domain"]  # ... domain каждого модуля
forbidden_modules = ["fastapi", "sqlalchemy", "pydantic", "httpx", "sklearn", "numpy"]
allow_indirect_imports = true

[[tool.importlinter.contracts]]
name = "core не знает о модулях"
type = "forbidden"
source_modules = ["src.core"]
forbidden_modules = ["src.modules", "src.web", "src.seed"]
```

- В каждом модуле есть все три пакета `presentation`, `application`, `domain`, хотя бы с пустым
  `__init__.py`.
- `application` может импортировать порты из `src.core.infrastructure.interfaces` и логгер, но не
  реализации.
- Контракт не ослабляем и в исключения не добавляем. Нарушение чиним портом и ACL (red line эталона,
  `AGENTS.md`, п. 4).
- Новый модуль вписываем во все пять контрактов.

---

## 4. `core`: общее ядро

`core` не знает о модулях. Это проверяет import-linter.

```
src/core/
├── config.py                      # Settings (pydantic-settings)
├── exceptions.py                  # базовые ошибки → HTTP-статусы
├── dto/pagination.py              # PageQuery, Page[T] (dataclass)
├── events/                        # DomainEvent, EventBus (Protocol) — минимально, см. ниже
├── schemas/
│   ├── problem_details.py         # формат ошибки
│   ├── pagination.py              # PageResponse[T] (Pydantic): {items, total}
│   └── types.py                   # SafeString
└── infrastructure/
    ├── logger.py                  # get_logger
    ├── database/
    │   ├── base.py                # Base + создание схем в create_all (как в эталоне)
    │   ├── database.py            # get_engine, get_async_session_maker
    │   ├── mixins.py              # UUIDMixin, TimeStampMixin
    │   ├── unit_of_work.py        # SqlAlchemyUnitOfWork (копия эталона)
    │   ├── schema.py              # CORE_SCHEMA = "core"
    │   ├── models/audit_log.py    # AuditLog (ADR-09)
    │   └── repositories/audit_log_repository.py
    ├── interfaces/                # порты, общие для модулей
    │   ├── unit_of_work.py        # UnitOfWorkInterface
    │   ├── llm_client.py          # LLMClientInterface, ChatMessage
    │   └── audit_log.py           # AuditLogInterface
    ├── llm/
    │   ├── openai_compatible.py   # адаптер к /v1/chat/completions (httpx)
    │   ├── null_client.py         # «LLM выключена»: всегда LLMUnavailableError
    │   └── structured.py          # complete_model(): валидация Pydantic + один повтор
    ├── dependencies.py            # get_settings, get_session, get_unit_of_work, get_llm_client, get_audit_log
    └── exception_handler.py       # register_core_handlers(app)
```

### Исключения

Сделаны как в эталоне (`DomainError`, `InfrastructureError`), но HTTP-статус определяется
**базовым классом**. Модуль наследует свою ошибку от нужной базы, а отдельный обработчик не пишет.

| Базовый класс (`src.core.exceptions`) | HTTP | Пример наследника |
| --- | --- | --- |
| `NotFoundError(DomainError)` | 404 | `OfficialNotFoundError`, `AppealNotFoundError` |
| `ConflictError(DomainError)` | 409 | `AppealAlreadyClosedError` (недопустимый переход статуса) |
| `DomainValidationError(DomainError)` | 422 | `InvalidRiskWeightError` |
| `DomainError` (прочие) | 400 | — |
| `ExternalServiceError(InfrastructureError)` | 503 | `LLMUnavailableError`, если фоллбэка нет |
| `InfrastructureError` (прочие) | 500 | — |

`LLMUnavailableError` и `LLMInvalidResponseError` — наследники `ExternalServiceError` в
`core/exceptions.py`. До HTTP они почти никогда не доходят: их перехватывает фоллбэк модуля.

### DTO и пагинация

`Page[T]` (`items: list[T]`, `total: int`) — общий результат списочных use case. `PageResponse[T]` —
его Pydantic-зеркало для ответа API. Списки отдаются как `{items, total}`. `limit` по умолчанию 20,
максимум 100, `offset ≥ 0`. Ограничения задаются в схеме запроса через `Query(le=100)`.

### События

В эталоне события публикуются в NATS (`training/infrastructure/adapters/event_bus.py`). У нас брокера
нет, а единственная межмодульная реакция синхронная (ADR-10) и идёт через порт. Поэтому в
`core/events` оставляем только базовый `DomainEvent` и протокол `EventBus` (копии
`core/events/base.py` и `event_bus.py` эталона). Реализацию `InProcessEventBus` пишем, когда на
один факт появится второй подписчик, не раньше.

### База и Unit of Work

- `Base` с `naming_convention`. Обработчик `before_create` создаёт схемы при `create_all` в тестах
  (как в эталоне).
- Движок и `async_sessionmaker` создаются в `lifespan` и кладутся в `app.state`. Сессия на запрос —
  `get_session`. Use case получает `UnitOfWorkInterface` (`get_unit_of_work`) и репозитории на той же
  сессии:

```python
async def execute(self, dto: SubmitAppealDTO) -> AppealDTO:
    analysis = await self._analyzer.analyze(dto.text)          # до транзакции: LLM медленная
    async with self._unit_of_work:
        appeal = Appeal.create(text=dto.text, channel=dto.channel)
        appeal.attach_analysis(analysis, linked_person_ids=...)  # инвариант — в агрегате
        await self._appeals.save(appeal)
        await self._unit_of_work.commit()                       # явный коммит
    await self._risk.recompute_for(appeal.linked_person_ids)    # после коммита, ADR-10
    return AppealDTO.from_entity(appeal)
```

Выход из блока без `commit()` откатывает изменения. Вложенный Unit of Work падает `RuntimeError`.
Use case не вызывает другой use case внутри своей транзакции.

### LLM-порт (ADR-05)

Порт общий для `appeals`, `reports` и `assistant`, поэтому лежит в `core`, как порты хранилищ в
эталоне (`core/infrastructure/interfaces/blob_storage.py`).

```python
# core/infrastructure/interfaces/llm_client.py
@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LLMClientInterface(Protocol):
    async def complete_json(
        self, system: str, messages: list[ChatMessage], schema: dict[str, Any]
    ) -> dict[str, Any]: ...
```

- **`OpenAICompatibleLLMClient`** (`llm/openai_compatible.py`) делает `POST {LLM_BASE_URL}/chat/completions`
  через `httpx.AsyncClient`. Параметры: `temperature=0`, `response_format` — `json_schema`, а если
  сервер его не принимает, то `json_object`. Таймаут ответа `LLM_TIMEOUT_SECONDS` (60 с), соединения —
  `LLM_CONNECT_TIMEOUT_SECONDS` (5 с). Ошибки сети, таймаут и 5xx превращаются в `LLMUnavailableError`,
  не-JSON ответ — в `LLMInvalidResponseError`. Один повтор только при 5xx/429 и обрыве установленного
  соединения; недоступный сервер и истёкший таймаут сразу ведут к фоллбэку. Каждый вызов
  логируется: модель, длительность, токены, валиден ли ответ. Текст обращения в лог не пишем.
- **`NullLLMClient`** всегда бросает `LLMUnavailableError`. Его отдаёт `get_llm_client`, если
  `LLM_BASE_URL` пуст, и его же подставляем в тестах.
- **`complete_model(client, system, messages, model: type[T]) -> T`** (`llm/structured.py`)
  валидирует ответ Pydantic-моделью. При ошибке повторяет запрос один раз и добавляет текст ошибки.
  Если и повтор не прошёл, бросает `LLMInvalidResponseError`.
- **Фоллбэк** — двухуровневый. Ядро даёт единый сигнал «LLM не справилась» (`LLMUnavailableError` /
  `LLMInvalidResponseError`). Модуль решает, чем её заменить: `appeals` — словарями и регулярками,
  `reports` — шаблоном, `assistant` — ответом «не могу ответить». Схема в модуле одна и та же:

```
appeals/application/interfaces/appeal_analyzer.py      # AppealAnalyzerInterface.analyze(text) -> AppealAnalysis
appeals/infrastructure/analyzers/llm_analyzer.py       # промпт + complete_model + схема ответа (Pydantic)
appeals/infrastructure/analyzers/rule_analyzer.py      # фоллбэк из ai.md
appeals/infrastructure/analyzers/fallback_analyzer.py  # FallbackAppealAnalyzer(primary, fallback): ловит LLM*Error,
                                                       # проставляет engine = "llm" | "fallback"
```

- Один `httpx.AsyncClient` на приложение создаётся в `lifespan` и закрывается при остановке.

### Журнал действий (ADR-09)

`AuditLog` (`id, actor, action, object_type, object_id, at`) лежит в схеме `core`, как
`s3_metadata` в эталоне: это сквозная запись, а не предметная область. Порт `AuditLogInterface.record(...)`
вызывают use case: открыть профиль, сформировать докладную, пересчитать риск. Аутентификации нет,
поэтому `actor` пока константа `"analyst"`.

---

## 5. Ошибки API, конфиг, логи, схемы, миграции

### Формат ошибок

Все ошибки отдаются в формате ProblemDetails (RFC 7807), как `core/schemas/problem_details.py`
эталона, с `Content-Type: application/problem+json`:

```json
{
  "title": "OfficialNotFoundError",
  "status": 404,
  "detail": "Служащий не найден",
  "instance": "/api/v1/officials/6f1c..."
}
```

- `title` — имя класса исключения. Фронт может ветвиться по нему, текст показывает из `detail`.
- `detail` пишем по-русски. В нём нет ПДн, SQL и трассировок.
- **422 (валидация запроса)** — перехватываем `RequestValidationError` (в эталоне этого нет, там
  остаётся формат FastAPI) и отдаём тот же формат с полем `errors`:

```json
{
  "title": "RequestValidationError",
  "status": 422,
  "detail": "Некорректные параметры запроса",
  "errors": [{"loc": ["query", "limit"], "msg": "Input should be less than or equal to 100"}]
}
```

- **500** — `{"title": "Internal Server Error", "status": 500}` без `detail`. Подробности пишем только
  в лог (`logger.exception`).
- Обработчики живут в `core/infrastructure/exception_handler.py` (`register_core_handlers`) и
  регистрируются на базовые классы из раздела 4. Модульный `exception_handler.py` заводим, только
  если ошибке нужен нестандартный статус или заголовок.
- `HTTPException` из use case и домена не бросаем: HTTP знает только `presentation`.

### Конфиг

`src/core/config.py`, `pydantic-settings`. `os.environ` в коде запрещён. Имена переменных
зафиксированы в [contracts.md](contracts.md), поэтому настройки **плоские**, без префикса
`KYOP__` и вложенности, в отличие от эталона:

```python
class Settings(BaseSettings):
    database_url: SecretStr                                    # DATABASE_URL
    cors_origins: Annotated[list[str], NoDecode] = []          # CORS_ORIGINS, через запятую
    llm_base_url: str = ""                                     # LLM_BASE_URL; пусто = NullLLMClient
    llm_api_key: SecretStr = SecretStr("")                     # LLM_API_KEY
    llm_model: str = "qwen2.5:7b-instruct"                     # LLM_MODEL
    llm_timeout_seconds: float = 60.0                          # LLM_TIMEOUT_SECONDS
    llm_connect_timeout_seconds: float = 5.0                   # LLM_CONNECT_TIMEOUT_SECONDS
    seed_dir: str = "data/generated"                           # SEED_DIR
    # LLM выключена, если LLM_BASE_URL пуст (свойство settings.llm_enabled)

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"), extra="ignore"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        return [s.strip() for s in v.split(",") if s.strip()] if isinstance(v, str) else v
```

- `get_settings_from_env()` обёрнута в `@lru_cache`. `create_app(settings)` принимает настройки
  параметром: тесты передают свои.
- Новая переменная: поле в `Settings`, строка-пример в корневом `.env.example` и строка в таблице
  `contracts.md`, если её задаёт DevOps.

### Логирование

```python
from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)
logger.info("Risk recomputed: {} persons, {} flags in {:.1f} ms", n_persons, n_flags, ms)
```

- `get_logger` можно импортировать из любого слоя. Это единственное исключение из правила
  направления зависимостей.
- Сообщения форматируем через `{}`, f-строки и `%s` не используем. `print` в коммит не попадает.
- **Не логируем** текст обращений, ФИО, ИНН, адреса, телефоны и `LLM_API_KEY`. Логируем id.
- Уровни как в эталоне: `info` — значимые события и ожидаемые пропуски, `warning` — сработал
  фоллбэк LLM, `error` — сбой операции.

### Схемы Postgres

Одна схема на модуль, в `public` только `alembic_version`. Имя схемы — константа в
`infrastructure/database/schema.py` модуля, модели указывают её в
`__table_args__ = {"schema": ...}`, FK внутри модуля пишутся со схемой (`"officials.persons.id"`).

| Схема | Модуль | Таблицы |
| --- | --- | --- |
| `officials` | officials | `organs`, `positions`, `authorities`, `persons`, `appointments`, `kinships` |
| `counterparties` | counterparties | `companies`, `company_roles`, `employments`, `contracts` |
| `risk` | risk | `risk_flags`, `risk_scores` |
| `appeals` | appeals | `appeals` (`analysis` — `jsonb`, `linked_person_ids` — `uuid[]`) |
| `reports` | reports | `report_drafts` |
| `core` | core | `audit_log` |

У `assistant` таблиц нет.

### Миграции

```sh
make makemigrations m="add risk tables"   # alembic revision --autogenerate
make migrate                              # alembic upgrade head
make downgrade                            # проверить откат
```

- `migrations/env.py` повторяет эталонный: async-движок, `target_metadata = Base.metadata`,
  `include_schemas=True` и **импорт всех моделей всех модулей**. Модель, которую забыли импортировать,
  autogenerate не увидит.
- Autogenerate **не создаёт схемы**. Миграция, в которой появляется новая схема, начинается с
  `op.execute("CREATE SCHEMA IF NOT EXISTS <name>")`, а `downgrade` заканчивается `DROP SCHEMA`
  (образец — `2026_10_28_1800-ef913316e14a_move_tables_to_context_schemas.py`).
- Результат autogenerate вычитываем руками: лишние `drop`, enum и индексы.
- Каждая миграция — новый файл, обратимая, `downgrade` прогнан локально. Уже влитую в `dev` или `main`
  миграцию не редактируем.
- Имена файлов задаёт шаблон из `alembic.ini` эталона:
  `%%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s`.
- Если миграции пишут двое одновременно, после `git pull` проверяем `uv run alembic heads`. Две головы
  сливаем `alembic merge heads -m "merge"`.
- В compose миграции применяются при старте контейнера (`alembic upgrade head && uvicorn ...`).

---

## 6. Целевая структура `backend/`

```
backend/
├── pyproject.toml            # зависимости, ruff, mypy, pytest, import-linter
├── uv.lock
├── .python-version           # 3.12
├── Makefile
├── Dockerfile                # по образцу optimus/Dockerfile: builder на uv → slim runtime
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
├── src/
│   ├── core/                 # раздел 4
│   ├── modules/
│   │   ├── officials/        # служащие, органы, должности, полномочия, родство; профиль и граф
│   │   ├── counterparties/   # компании, роли в компаниях, прошлая работа, контракты
│   │   ├── risk/             # правила R01–R08, скоринг, пересчёт
│   │   ├── appeals/          # обращения, анализ (LLM + фоллбэк), сопоставление лиц
│   │   ├── reports/          # черновики докладных, сводка для главной
│   │   └── assistant/        # LLM-ассистент на закрытом наборе инструментов
│   ├── web/
│   │   ├── main.py           # app = create_app(get_settings_from_env())
│   │   ├── create_app.py     # lifespan, CORS, обработчики, роутеры под /api/v1, overrides, /health
│   │   └── dependencies.py   # сборка ACL-адаптеров: здесь видны все модули
│   └── seed/                 # python -m src.seed: загрузка data/generated/*.json (второй composition root)
│       ├── __main__.py
│       └── loader.py
└── tests/
    ├── conftest.py
    ├── unit/<module>/{domain,application}/
    ├── integration/<module>/
    └── e2e/<module>/
```

`src/seed` знает все модули, как и `web`. Он читает JSON из `SEED_DIR`, вызывает
`Import*UseCase` каждого модуля, затем делает предрасчёт анализа фоновых обращений (ADR-05) и полный
пересчёт риска. Каталог `data/` вне контекста сборки образа, поэтому в compose нужен том
`./data:/app/data:ro` (с Кириллом).

### Сущности контракта по модулям и слоям

| Модуль | `domain` | `application` (основные use case) | Порты к чужим модулям |
| --- | --- | --- | --- |
| `officials` | `Person`, `Organ` (агрегаты). `Position`, `Authority`, `Appointment`, `Kinship` — внутри них. Enum `AuthorityKind`, `KinshipKind`. Правило «служащий = Person с Appointment» | `ListOfficials` (рейтинг), `GetOfficialProfile`, `GetOfficialGraph`, `ListOrgans`, `GetOfficialsSnapshot` (для ACL), `ImportOfficials` | `RiskSummarySource` ← risk, `CompanyLinksSource` ← counterparties, `AppealLinksSource` ← appeals |
| `counterparties` | `Company` (агрегат с `CompanyRole`), `Contract`, `Employment`. Enum `CompanyRoleKind` | `GetCounterpartiesSnapshot`, `GetCompanyLinks(person_ids)`, `LookupCompany`, `ImportCounterparties` | — |
| `risk` | `RiskFlag`, `RiskScore`, VO `EvidenceNode`, `RiskWorld` и `facts.py` (факты в терминах риска), `RiskRule`, правила `rules/r0N_*.py`, `score.py` (`ScorePolicy`), граф связей, enum `RuleCode`, `Severity` | `RecomputeRisk` (все или `person_ids`), `GetFlags`, `GetRiskSummaries(person_ids)`, `GetRiskStats` | `OfficialsSource` ← officials, `CounterpartiesSource` ← counterparties, `AppealSignalsSource` ← appeals, `PeerAnomalyDetector` (ML, адаптер в своём `infrastructure/ml/`) |
| `appeals` | `Appeal` (агрегат, статусы `new → analyzed → routed → closed`), VO `AppealAnalysis`, `ExtractedEntity`, `Signal`, `specificity.py`, `routing_policy.py` | `SubmitAppeal`, `ReanalyzeAppeal`, `ListAppeals`, `GetAppeal`, `GetAppealSignals` (для R07), `GetAppealStats` | `AppealAnalyzer` и `PersonMatcher` (адаптеры ИИ в своём `infrastructure/`), `OfficialsDirectory` ← officials, `RiskRecalculator` → risk |
| `reports` | `ReportDraft`, VO `ReportFacts`. Правило «в тексте только факты из входа» | `CreateReportDraft`, `GetReportDraft` | `ReportFactsSource` ← officials, risk, appeals; `ReportWriter` (шаблон Jinja или LLM) |
| `stats` | — (своих данных нет) | `GetOverview` (`/stats/overview`) | счётчики ← officials, risk, appeals |
| `assistant` | VO `ToolCall`, `AssistantAnswer`, `Source`. Закрытый список инструментов и их аргументов, лимит 3 шага | `AskAssistant` | инструменты из [ai.md](ai.md), §6, каждый — порт на use case чтения чужого модуля |
| `core` | — | — | `AuditLog` (раздел 4) |

Пояснения к раскладке:

- **Путь URL не равен модулю.** `/officials/{id}/flags` и `/officials/{id}/graph` обслуживает
  роутер `risk`, `/stats/overview` — модуль `stats` (ADR-15). Все роутеры подключаются в `create_app.py` с
  `prefix="/api/v1"`. `/health` — без префикса.
- **Рейтинг `/officials`.** Служащих около 150 (ADR-03), поэтому `ListOfficials` берёт служащих по
  `query` и `organ_id` из своего репозитория, а баллы и `top_flags` — через `RiskSummarySource`.
  Фильтр `min_score`, сортировка и пагинация делаются в памяти. Если данных станет на порядки больше,
  переходим на read-модель по образцу `projector` эталона.
- **Граф `/officials/{id}/graph`** собирается в `risk` (ADR-15) обходом в ширину до `depth` через
  те же порты, что и снимок для правил. id узла — UUID сущности. `evidence` флага — список
  `{node_id, type, label}` тех же узлов, поэтому фронт может подсветить цепочку.
- **ИИ-функции Влада О.** (`analyze_appeal`, `match_persons`, `peer_anomalies`, `draft_report`)
  встают адаптерами за портами модулей: `appeals/infrastructure/analyzers/`,
  `appeals/infrastructure/matching/`, `risk/infrastructure/ml/`, `reports/infrastructure/writers/`.
  `specificity` и маршрутизация — формулы, поэтому живут в `appeals/domain`. Формула R07 живёт в
  `risk/domain`.

### Риск-движок (ADR-04: методика балла)

```python
# risk/domain/rules/base.py
class RiskRule(ABC):
    code: ClassVar[RuleCode]
    severity: ClassVar[Severity]
    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]: ...
```

- **Правила — чистые функции над снимком (ADR-13).** `RecomputeRiskUseCase` собирает снимок `RiskWorld`:
  служащие, должности, полномочия, родство (из `OfficialsSource`), компании, роли, прошлая работа,
  контракты (из `CounterpartiesSource`), сигналы обращений (из `AppealSignalsSource`). Затем он
  прогоняет все правила из реестра `default_rules()` в `risk/domain/rules/__init__.py`, добавляет флаги R08 от
  `PeerAnomalyDetector`, считает баллы и в одной транзакции заменяет флаги и баллы пересчитанных лиц.
  Граф маленький, снимок целиком помещается в память. Правила тестируются без БД, а риску не нужны
  join по чужим схемам.
- **Каждый флаг** обязан иметь `explanation`, `evidence` (непустая цепочка узлов) и `legal_ref`, если
  норма есть. Это инвариант конструктора `RiskFlag`. Формулировки — «может свидетельствовать»
  (ADR-09).
- **Балл** (`ScorePolicy` в `risk/domain/score.py`), веса — константы в одном месте. Стартовые веса
  подтверждены на созвоне по контракту (T-01), откалиброваны по `_truth` 15.11 (B-17, ADR-16):

| Severity | Вес | До B-17 |
| --- | --- | --- |
| high | 40 | 40 |
| medium | 20 | 20 |
| low | 5 | 7 |
| R08 (ML) | 3 (low) / 5 (medium) — не тяжелее самого лёгкого правила, ML один не выводит в топ | 5 / 10 |

  `score = min(100, Σ вклад правил)`. Вклад правила — вес его самого тяжёлого флага. Каждый
  следующий флаг того же правила добавляет половину своего веса, всего не больше двух весов правила.
  Пример: R01 high + два R05 medium + R06 low = 40 + (20 + 10) + 5 = 75. Десять флагов R05 дают
  не 200, а 40. При равном балле сортируем по `flags_count`. Инвариант калибровки: слабые сигналы
  (два `low` и R08 `medium`) вместе не больше `medium − 5`. При смене весов меняем только константы
  и тесты: эталонные профили в `tests/unit/risk/test_engine_and_score.py` и порядок демо на полном
  наборе в `tests/e2e/risk/test_demo_ranking.py`.
- **R08 (ML)** подключается через порт `PeerAnomalyDetectorInterface.detect(world) -> list[PeerAnomalyFacts]`
  (`risk/application/interfaces/peer_anomaly_detector.py`). Адаптер с моделью кладём в
  `risk/infrastructure/ml/` и отдаём из `get_peer_anomaly_detector()` в
  `risk/presentation/dependencies.py`; пока там `NoPeerAnomalyDetector`. Детектор работает только
  при полном пересчёте (нужна вся группа коллег), при частичном прошлые флаги R08 переносятся.
  Правило `PeerAnomalyRule` пишет объяснение по трём признакам с наибольшим |z|.
- **Пересчёт** запускается тремя путями: `POST /risk/recompute` (все), `make seed` (все, в конце
  загрузки) и `RecomputeRiskUseCase.execute(person_ids)` после анализа обращения — подписчик события
  `AppealAnalyzedEvent` в `web/event_handlers.py` (ADR-10). Пересчёт синхронный.

---

## 7. Пошагово

### Добавить модуль

1. Создать `src/modules/<m>/` с пакетами `domain`, `application`, `infrastructure`, `presentation`
   (раскладка в разделе 3). Образец — `waitlist` эталона.
2. `infrastructure/database/schema.py`: `<M>_SCHEMA = "<m>"`.
3. Вписать модуль во все контракты import-linter (раздел 3).
4. Импортировать модели модуля в `migrations/env.py`. Сделать миграцию с `CREATE SCHEMA` (см. ниже).
5. Подключить роутер в `create_app.py` (`app.include_router(router, prefix="/api/v1")`), заглушки
   чужих портов — в `app.dependency_overrides`.
6. Создать `tests/unit/<m>/`, `tests/integration/<m>/`, `tests/e2e/<m>/`.
7. `make lint` зелёный.

### Добавить эндпоинт

1. Сверить путь, параметры и ответ с [contracts.md](contracts.md). Если меняется контракт, правим
   `contracts.md` в том же PR.
2. `domain`: если появляется правило — метод агрегата или политика плюс доменное исключение от нужной
   базы (`NotFoundError`, `ConflictError`, ...).
3. `application/dto/`: входной и выходной `@dataclass`. `application/use_cases/<action>.py`:
   `<Action>UseCase.execute(dto) -> ResultDTO`, зависимости по портам. Транзакция — через Unit of Work.
4. `infrastructure`: если нужен новый метод репозитория — добавить его в порт и в реализацию. Список
   делаем с `limit`.
5. `presentation/schemas/`: request и response на Pydantic, пользовательский текст типом `SafeString`,
   `limit: int = Query(20, ge=1, le=100)`.
6. `presentation/dependencies.py`: фабрика `get_<action>_use_case`.
7. `presentation/api/<m>_router.py`: тонкий хендлер с `response_model` и `status_code`.
8. Тесты: unit на use case (успех и ожидаемый отказ), e2e на успех, 404 и 422.

### Добавить правило риска

1. Значение в `RuleCode` (`risk/domain/enums.py`), строка в таблице правил `contracts.md`.
2. `risk/domain/rules/rNN_<name>.py`: класс с `code` и `evaluate(snapshot) -> list[RiskFlag]`.
   Severity, `explanation` по-русски («может свидетельствовать»), `evidence` — цепочка узлов графа
   (`EvidenceNode(type, id, label)`, в API — `{node_id, type, label}`) от служащего до объекта, `legal_ref`.
3. Не хватает фактов в `RiskWorld` — расширить факты снимка (`risk/domain/facts.py`), `RiskWorldLoader`, порт источника, ACL-адаптер и use case
   снимка в модуле-источнике. Чужой модуль не импортировать.
4. Зарегистрировать правило в реестре `risk/domain/rules/__init__.py`.
5. Unit-тесты на снимке, собранном руками: срабатывание, несрабатывание и ложноположительный кейс из
   [data.md](data.md) (правило молчит или ослабляет флаг).
6. `POST /risk/recompute` на сидах. Заложенные кейсы в топе, `make eval` не просел.

### Добавить миграцию

1. Поменять ORM-модель в `infrastructure/database/models/`. Если модель новая — импортировать её в
   `migrations/env.py`.
2. `make makemigrations m="..."`, вычитать файл. Для новой схемы вписать `CREATE SCHEMA IF NOT EXISTS`
   в начало `upgrade` и `DROP SCHEMA` в конец `downgrade`.
3. Не делать FK на таблицы чужого модуля.
4. `make migrate && make downgrade && make migrate` на локальной БД.
5. `uv run alembic heads` — одна голова.

### Добавить межмодульный порт

1. Порт в потребителе: `<consumer>/application/interfaces/<what>_source.py`, в терминах потребителя.
2. Заглушка в `<consumer>/presentation/dependencies.py`, которая бросает `NotImplementedError` (как
   `get_relationship_checker` эталона).
3. Use case чтения в модуле-источнике, если его ещё нет.
4. ACL-адаптер `<consumer>/infrastructure/adapters/<source>_acl.py` с локальным `Protocol` источника.
5. Сборка в `web/dependencies.py`, подмена заглушки в `create_app.py`.

---

## 8. Тесты

Уровень определяется слоем, как в эталоне (`.agents/optimus/testing.md`).

| Каталог | Что тестирует | Инфраструктура |
| --- | --- | --- |
| `tests/unit/<module>/` | `domain` и `application`: агрегаты, VO, правила R01–R08, скоринг, `specificity`, маршрутизация, use case | никакой. Порты заменены фейками в памяти или `AsyncMock`, LLM — `NullLLMClient` или фейк с заготовленным JSON |
| `tests/integration/<module>/` | `infrastructure`: репозитории, ACL-адаптеры, адаптер LLM, миграции | реальный Postgres. LLM — `httpx.MockTransport` |
| `tests/e2e/<module>/` | HTTP → use case → БД → ответ через `httpx.AsyncClient(transport=ASGITransport(app))` | реальный Postgres, `create_app(test_settings)`, LLM подменён через `dependency_overrides` |

- **Postgres в тестах** поднимаем двумя способами, как в `optimus/tests/integration/conftest.py`.
  Локально — `testcontainers` (`PostgresContainer("postgres:16", driver="asyncpg")`). При
  `CI == "true"` берём `DATABASE_URL`: в нашем CI Postgres уже поднят сервисом. Новая фикстура
  обязана поддерживать оба режима.
- Схема в integration и e2e создаётся через `Base.metadata.create_all`, после теста таблицы
  очищаются (`clean_tables` в эталоне). Отдельный тест проверяет, что `alembic upgrade head` и
  `downgrade base` проходят на пустой БД.
- БД в тестах репозиториев не мокаем. Домен и `application` в unit-тестах не ходят в БД.
- Фикстуры кладём в `conftest.py` ближайшего уровня. Хелперы-не-фикстуры — в `tests/_*.py`.
- Структура теста: Arrange / Act / Assert. Имя — `test_<что>_<при_каком_условии>`. Время фиксируем
  `freezegun`, id передаём явно.

**Обязательно покрываем:**

- каждое правило R01–R08: срабатывание, несрабатывание, ложноположительный кейс;
- скоринг: нормировка, потолок R08, порядок топа на эталонных случаях;
- `specificity`, маршрутизацию, переходы статусов `Appeal` (разрешённые и запрещённые);
- фоллбэк: LLM недоступна, невалидный JSON, повтор, `engine = "fallback"`;
- каждый эндпоинт: e2e на успех и на 404 или 422;
- исправленный баг: тест, который падает без исправления.

**Команды** (из `backend/`):

```sh
make test-unit          # быстро, ничего не нужно
make test-integration   # нужен Docker (testcontainers)
make test-e2e
make test               # всё
make lint               # ruff + format --check + mypy + lint-imports
```

Из корня: `make test-back`, `make lint-back`.

---

## 9. Где мы намеренно отличаемся от эталона

| Тема | Эталон | У нас | Почему |
| --- | --- | --- | --- |
| Межмодульные события | NATS + FastStream, `EventBus` на модуль | брокера нет, реакция ADR-10 — синхронный порт | один процесс, 3 дня |
| Аутентификация и доступ | JWT RS256, `core/access`, политики на строки | нет, `actor = "analyst"` | в контракте нет |
| Хранилище файлов | S3 (Silo) | нет | файлов нет |
| Конфиг | `KYOP__SECTION__KEY`, вложенные модели | плоские `DATABASE_URL`, `LLM_*`, `CORS_ORIGINS` | имена зафиксированы контрактом и `.env.example` |
| Обработчики ошибок | по функции на исключение | по базовому классу в `core` | меньше кода, единый формат |
| Ошибка валидации 422 | формат FastAPI | ProblemDetails + `errors` | один формат для фронта |
| Контракты import-linter | по 3 на модуль | `containers` + `independence` + запрет фреймворков в `domain` | короче, строже к домену |
| Коммит | местами в репозитории | только Unit of Work в use case | переходный код эталона не копируем |
| Read-side | модуль `projector` (проекции из событий) | чтения через порты и join в памяти | данных мало, событий нет |
| ИИ и ML | нет | порт LLM в `core`, адаптеры ИИ и ML в модулях | ADR-05, ADR-08 |
| Наполнение БД | нет | `src/seed` — второй composition root | `make seed` из плана |
