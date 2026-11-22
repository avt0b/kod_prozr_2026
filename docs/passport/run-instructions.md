# Инструкция запуска прототипа «Код прозрачности»

Команда battalion_404 · репозиторий https://github.com/avt0b/kod_prozr_2026 · ветка `main`, релиз v1.0.1.
Документ входит в состав сдаваемого архива (блок 10 паспорта проекта).

## 1. Что нужно на машине

| Компонент | Версия | Обязательность |
| --- | --- | --- |
| Docker Engine + Compose | Compose v2.24+ | обязательно |
| GNU make | любая актуальная | обязательно (все команды через Makefile) |
| bash | Git Bash / WSL / Linux | обязательно: `Makefile` задаёт `SHELL := /bin/bash` |
| Python | 3.12 (в образе бэкенда); на хосте 3.10+ для генератора и smoke | обязательно для `make data`, `make smoke` |
| uv | 0.5+ | только для `make test-back`, `make eval`, `make precompute` на хосте |
| Node.js + npm | Node 22.18+ | только для линта, сборки и e2e фронта на хосте |
| NVIDIA GPU + nvidia-container-toolkit | ~5 ГБ свободной VRAM | опционально, для локальной LLM |

Ресурсы: без LLM — от 2 vCPU и 4 ГБ RAM; с `qwen2.5:7b-instruct` на CPU — от 4 vCPU и 12–16 ГБ RAM (модель ~4,7 ГБ на диске). Свободного места на диске — не менее 15 ГБ с LLM.

Версии зависимостей зафиксированы: `backend/uv.lock`, `frontend/package-lock.json`, образы в `.env.example`. Отдельно устанавливать зависимости для запуска в Docker не нужно — они внутри образов.

## 2. Быстрый запуск (без LLM, 5 шагов)

```bash
git clone https://github.com/avt0b/kod_prozr_2026.git
cd kod_prozr_2026
cp .env.example .env          # или: make env
make up                       # сборка образов и подъём postgres + backend + frontend
make seed                     # миграции и загрузка синтетики с предрасчётом
```

Проверка готовности:

```bash
make ps                                   # все сервисы healthy
curl -fsS localhost:8000/health           # {"status":"ok"}
```

Адреса: интерфейс http://localhost:3000 · API http://localhost:8000/api/v1 · Swagger http://localhost:8000/docs.

В режиме без LLM разбор обращений идёт на правилах и словарях (в карточке виден бейдж «Разбор: правила (фоллбэк)»), докладная строится по шаблону, ассистент отвечает на типовые вопросы детерминированно. Ключевой сценарий работает целиком.

Порты заняты — переопределите в `.env`: `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`, `VITE_API_URL`.

## 3. Запуск с локальной LLM (опционально)

```bash
make llm-up                   # поднимет Ollama, скачает и прогреет qwen2.5:7b-instruct
make llm-check                # проверит, что бэкенд видит LLM_BASE_URL
```

В `.env` установите:

```
LLM_BASE_URL=http://ollama:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5:7b-instruct
LLM_TIMEOUT_SECONDS=90
```

Затем `make up`. Первая загрузка модели в память занимает около минуты; разбор одного обращения на GPU 8 ГБ — 2–5 с, запрос `POST /appeals` целиком — 5–6 с. Если GPU нет, `make llm-up` сообщит, что Ollama работает на CPU (медленнее). Для слабой машины подойдёт `LLM_MODEL=qwen2.5:3b-instruct` (~2 ГБ). Ollama на хосте вместо контейнера: `LLM_BASE_URL=http://host.docker.internal:11434/v1` и `OLLAMA_HOST=0.0.0.0`.

## 4. Ключевой сценарий для проверки (5–7 минут)

Полный сценарий с таймингом — `docs/demo.md`. Кратко:

1. Главная http://localhost:3000 — счётчики: 162 служащих, 106 обращений.
2. Рейтинг — Соколов Андрей Викторович **не на 1-м месте** (балл 73, 3-е место).
3. Обращения → «Новое» → вставить текст из `demo/appeal_h1.txt`, канал `web`, отправить.
4. Карточка разбора: категория, подсвеченные ФИО, должность, компания, сумма, дата, сигналы, конкретность, маршрут, привязка «Соколов А. В.».
5. Рейтинг — Соколов поднялся на **1-е место, балл 88** (отрыв 8).
6. Профиль Соколова — флаги R01, R05, R06, R07, R08 с объяснением и нормой; клик по R01 подсвечивает в графе цепочку «Соколов → супруга → ООО "ДорСтройРесурс" → 5 контрактов на 38 млн → его департамент».
7. «Сформировать докладную» — черновик с фактами, нормами и пометкой «решение принимает уполномоченное лицо».
8. Рейтинг с фильтром по правилу: R02 → Лебедева, R03 → Гусев, R04 → Морозов, R05 → Белова; Орлов (ложное обвинение) внизу.
9. Ассистент: «Покажи служащих, у которых родственники среди подрядчиков их органа».

Автоматическая проверка всего сценария: `make smoke` (50 проверок) или Playwright-прогон из раздела 5.

**Важно:** smoke и e2e отправляют демо-обращение и меняют данные. После них выполните `make reset`, чтобы вернуть исходное состояние (Соколов не первый). Проверить стенд без изменения данных: `python3 scripts/smoke.py --keep-demo`.

## 5. Проверки и тесты

```bash
# данные (нужен только Python на хосте)
python -m unittest discover -s data/tests -t .    # 6 тестов генератора
make data-check                                   # валидация набора и sample
make data                                         # перегенерация с --seed 42

# бэкенд (нужен uv на хосте и поднятый postgres)
make test-back                                    # pytest, включая e2e на PostgreSQL
make lint-back                                    # ruff, mypy strict, import-linter

# фронтенд (нужен Node 22+)
cd frontend && npm ci
npm run lint && npm run build && npm test         # линт, сборка, unit-тесты
npx playwright install chromium
BASE_URL=http://localhost:3000 API_URL=http://localhost:8000/api/v1 npm run e2e

# стенд и метрики
make smoke                                        # 50 проверок API + демо-обращение
make eval                                         # метрики качества -> eval/report.json
make eval EVAL_ARGS="--llm --limit 30"            # то же с LLM
```

Фактические результаты прогонов — `docs/passport/testing-report.md`.

### 5.1. Проверки без внешних зависимостей (только Python на хосте)

Эти скрипты не требуют Docker, uv и Node.js — ими удобно проверять данные и логику на любой машине:

```bash
python scripts/passport/verify_data.py       # тесты генератора, data-check, детерминизм, целостность
python scripts/passport/verify_domain.py     # методика балла и формулы разбора обращений
python scripts/passport/build_passport_docx.py  # пересборка паспорта .docx из passport.md
python scripts/passport/verify_passport.py   # проверка паспорта: 10 блоков, поля, состав команды
```

Отчёты пишутся в `dist/` (каталог в `.gitignore`). Каждый скрипт возвращает ненулевой код при провале проверки.

## 6. Сброс, дамп и офлайн-режим

```bash
make reset                    # снести тома, поднять стек, миграции и сиды — «как перед демо»
make dump                     # дамп БД в dist/db/kodprozr-<дата>.sql.gz
make restore FILE=dist/db/kodprozr-<дата>.sql.gz
make down                     # остановить стек (данные в томах сохраняются)
make logs s=backend           # логи одного сервиса
make help                     # список всех команд
```

Работа без интернета (резервная машина):

```bash
# на подготовленной машине с сетью
make offline-bundle                                   # образы, модель, .env, исходники, дамп -> dist/offline/
# перенести каталог dist/offline на резервную машину, затем
make offline-load OFFLINE_DIR=<путь к пакету>
make reset OFFLINE=1                                  # без сборки и без обращений к registry
make smoke
```

Офлайн-пакет занимает около 6,5 ГБ (образы + Ollama 0.12.6 + модель).

## 7. Видео-бэкап демонстрации

```bash
cd frontend && npm ci && npx playwright install chromium && cd ..
make reset
make video                    # Playwright-сценарий демо, видео в dist/video/
```

Сценарий `frontend/e2e/demo.spec.ts` проходит все шаги `docs/demo.md` в браузере 1920×1080 и записывает видео (пауза между действиями `DEMO_SLOWMO=400` мс). Длительность — в пределах регламента 10 минут.

## 8. Если что-то не работает

| Симптом | Причина и решение |
| --- | --- |
| `make up` зависает на сборке | Docker bridge-сеть не выходит в интернет (VPN/TUN). Сборка по умолчанию идёт в сети хоста; попробуйте `make build BUILD_NETWORK=default` или отключите VPN |
| Порт занят | Переопределите `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT` и `VITE_API_URL` в `.env`, затем `make up` |
| Пустой рейтинг | Не загружены сиды: `make seed` |
| `make smoke` падает | Стенд не поднят или уже прогонялся smoke: `make reset`, затем `make smoke` |
| Соколов сразу первый | Демо-обращение уже отправляли: `make reset` или `make restore` |
| Разбор обращения идёт дольше 20 с | LLM не прогрета или работает на CPU. Прогрейте модель (`make llm-up`) или отключите LLM: `LLM_BASE_URL=` в `.env`, затем `make up` — сценарий пойдёт на фоллбэке |
| Ollama не видит GPU | Нет nvidia-container-toolkit: Ollama молча работает на CPU. Установите toolkit или запустите Ollama на хосте |
| Бэкенд не видит Ollama на хосте | Файрвол отбрасывает пакеты: нужен `OLLAMA_HOST=0.0.0.0` и правило для порта 11434; отказ соединения даёт фоллбэк через 5 с |
| `make test-back` не находит uv | Установите uv или запускайте тесты в контейнере бэкенда |

## 9. Состав репозитория

```
kod_prozr_2026/
├── backend/          FastAPI, Python 3.12, DDD-модули, миграции Alembic, тесты
├── frontend/         React + TypeScript + Vite, экраны, граф, e2e Playwright
├── data/             генератор синтетики, готовый набор generated/ и разметка _truth/
├── docs/             контракты, решения (ADR), сценарий демо, паспорт проекта
│   ├── passport/     паспорт проекта (.docx и .md), эта инструкция, отчёт о тестировании
│   └── presentation/ презентация и скриншоты стенда
├── eval/             отчёты о качестве: report.json, report.llm.json
├── scripts/          smoke, offline, bench_llm, проверка регламента
├── docker-compose.yml, Makefile, .env.example
└── demo/appeal_h1.txt  текст демо-обращения
```
