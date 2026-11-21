# DevOps: запуск, dev-режим, LLM, деплой

Процесс команды — [workflow.md](workflow.md). Две постоянные ветки: `dev` для интеграции,
`main` для релизов. Прод-деплой: тег `vMAJOR.MINOR.PATCH` на коммите из `main`, ключ только
в GitHub Secrets. Конвейер, откат и ручное включение защиты веток описаны в разделе 7.
Локальные команды ниже сами по себе не дают разрешения на деплой в прод.

Ответственный — Кирилл. Срок сдачи — 13 ноября 2026. Порты и переменные задаёт
[contracts.md](contracts.md); если они меняются, этот файл обновляется вместе с ним.

## 1. Схема сервисов

```
                    браузер
             │                    │
   :3000 (prod) / :5173 (dev)    :8000  (браузер ходит на /api/v1 фронта, nginx → backend:8000)
             │                    │
   ┌─────────▼────────┐   ┌───────▼──────────┐        ┌──────────────────────┐
   │ frontend         │   │ backend          │ HTTP   │ ollama  (профиль llm)│
   │ nginx + статика  │   │ FastAPI/uvicorn  ├───────►│ :11434, /v1 — OpenAI │
   │ (vite build)     │   │ + alembic        │        │ том ollama_models    │
   └──────────────────┘   └───────┬──────────┘        └──────────────────────┘
                                  │ postgres:5432          или облачный/vLLM endpoint
                          ┌───────▼──────────┐
                          │ postgres 16      │
                          │ том postgres_data│
                          └──────────────────┘
```

| Сервис     | Образ / сборка                | Хост-порт        | Внутри сети      | Healthcheck                    |
| ---------- | ----------------------------- | ---------------- | ---------------- | ------------------------------ |
| `postgres` | `postgres:16.15-alpine`       | 5432             | `postgres:5432`  | `pg_isready`                   |
| `backend`  | `./backend/Dockerfile`        | 8000             | `backend:8000`   | `GET /health` → 200            |
| `frontend` | `./frontend/Dockerfile`       | 3000 (dev: 5173) | `frontend:80`    | `GET /` → 200                  |
| `ollama`   | `ollama/ollama:0.12.6` (профиль llm) | 11434     | `ollama:11434`   | `ollama list`                  |

Порядок старта: `postgres` (healthy) → `backend` (сначала `alembic upgrade head`, затем uvicorn) →
`frontend`. Порты публикуются на `BIND_HOST` (по умолчанию `127.0.0.1`).

Хост-порты по умолчанию из [contracts.md](contracts.md). Если на машине порт уже занят другим
проектом, его можно сдвинуть в `.env` (`POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`,
`OLLAMA_PORT`); внутри сети compose порты не меняются. `VITE_API_URL=/api/v1` от хост-портов
не зависит.
`make smoke`, `make eval`, `make precompute` и `make video` берут порты из того же `.env`.

Браузер обращается к API по `VITE_API_URL=/api/v1`, то есть к тому же origin, что и фронт:
nginx фронта (`frontend/nginx.conf`) проксирует `/api/` на `backend:8000`. Так refresh-cookie
входа (`SameSite=Strict`, [auth.md](auth.md)) работает и на `localhost:3000`, и на
`127.0.0.1:3000`. `CORS_ORIGINS` нужен для `npm run dev` и для проверки Origin в refresh/logout.
На VPS оба сервиса стоят за одним доменом (раздел 6).

## 2. Переменные окружения

Все переменные лежат в одном `.env` в корне репо (шаблон — `.env.example`). Docker Compose
подставляет их в `docker-compose.yml`, контейнер `backend` получает их через `env_file`.

| Переменная                       | Кто читает        | По умолчанию / пример                                           |
| -------------------------------- | ----------------- | --------------------------------------------------------------- |
| `POSTGRES_USER/PASSWORD/DB`      | postgres          | `kodprozr` / `kodprozr` / `kodprozr`                            |
| `DATABASE_URL`                   | backend           | `postgresql+asyncpg://kodprozr:kodprozr@postgres:5432/kodprozr` |
| `CORS_ORIGINS`                   | backend           | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000` |
| `LLM_BASE_URL`                   | backend           | `http://ollama:11434/v1`                                        |
| `LLM_API_KEY`                    | backend           | `ollama` (для Ollama — любая непустая строка)                   |
| `LLM_MODEL`                      | backend, Makefile | `qwen2.5:7b-instruct`                                           |
| `LLM_TIMEOUT_SECONDS`            | backend           | `90` — ожидание ответа (генерации) LLM                          |
| `LLM_CONNECT_TIMEOUT_SECONDS`    | backend           | `5` — ожидание соединения; затем сразу фоллбэк, без повтора     |
| `VITE_API_URL`                   | frontend (сборка) | `/api/v1` — через прокси nginx фронта                           |
| `AUTH_SECRET`                    | backend           | ключ JWT ≥ 32 символов; пустой `make env` заполнит случайным     |
| `AUTH_ACCESS_SECONDS` / `AUTH_REFRESH_DAYS` | backend | `900` / `7`                                                  |
| `FORWARDED_ALLOW_IPS`            | backend (compose) | частные сети: от них uvicorn берёт IP клиента из `X-Forwarded-For` (лимит входа) |
| `AUTH_COOKIE_SECURE`             | backend           | `false` локально по HTTP; `true` на VPS с HTTPS                  |
| `BACKEND_APP`                    | compose           | `src.web.main:app` — путь к ASGI-приложению для uvicorn         |
| `BIND_HOST`                      | compose           | `127.0.0.1`; `0.0.0.0` — показать демо по локальной сети        |
| `POSTGRES_IMAGE`                 | compose           | `postgres:16.15-alpine`                                         |
| `OLLAMA_IMAGE`                   | compose           | `ollama/ollama:0.12.6` (закреплено, см. §5)                     |
| `POSTGRES_PORT` / `BACKEND_PORT` | compose, Makefile | `5432` / `8000` — хост-порты, если стандартные заняты           |
| `FRONTEND_PORT` / `OLLAMA_PORT`  | compose, Makefile | `3000` / `11434`                                                |
| `OLLAMA_BIND_HOST`               | compose           | как `BIND_HOST`; `0.0.0.0` — раздать Ollama команде (§5)         |
| `BUILD_NETWORK`                  | Makefile, compose | `host` в `make build`; `default` — сборка в bridge-сети          |
| `LLM_GPU`                        | Makefile          | `auto` — GPU для `make llm-up`, если есть runtime `nvidia`       |

Важно:

- `DATABASE_URL` указывает на хост `postgres`, то есть на имя сервиса в compose. Если бэк
  запускается на хосте, замените хост на `localhost`.
- `VITE_API_URL` попадает в бандл при сборке. Чтобы новое значение подействовало, пересоберите
  фронт: `make build && make up`.

## 3. Команды

Полный список выводит `make help`.

| Команда           | Что делает                                                                  |
| ----------------- | --------------------------------------------------------------------------- |
| `make up`         | создаёт `.env`, если его нет, собирает образы и поднимает стек в фоне        |
| `make down`       | останавливает стек вместе с ollama; данные в томах сохраняются               |
| `make build`      | пересобирает образы (в сети хоста, см. ниже)                                |
| `make logs`       | показывает логи всех сервисов; один сервис: `make logs s=backend`            |
| `make ps`         | показывает состояние контейнеров и healthchecks                             |
| `make migrate`    | `alembic upgrade head` в одноразовом контейнере backend                      |
| `make seed`       | загружает `data/generated` с предрасчётом обращений и пересчитывает риск      |
| `make reset`      | сносит БД, поднимает стек с миграциями и сидами — состояние «как перед демо»; ollama и модели не трогает |
| `make smoke`      | smoke всех эндпоинтов + демо-обращение (меняет данные: затем `make reset`)    |
| `make data`       | пересоздаёт синтетику генератором (`seed 42`), затем нужен `make precompute`  |
| `make data-check` | проверки данных data.md §7 (полный набор и `sample/`)                         |
| `make precompute` | предрасчёт анализа обращений в сиды (AI-06), демо-обращение остаётся `new`    |
| `make eval`       | метрики качества по БД после сидов, `eval/report.json`                        |
| `make test-data`  | тесты генератора                                                             |
| `make test-back`  | `uv run pytest` в `backend/` на хосте                                       |
| `make lint-back`  | `ruff check` + `ruff format --check` в `backend/` на хосте                  |
| `make lint-front` | `npm run lint` в `frontend/` на хосте                                        |
| `make llm-up`     | поднимает ollama (GPU, если есть), скачивает и прогревает модель `LLM_MODEL` |
| `make llm-check`  | проверяет из контейнера backend, что `LLM_BASE_URL` отвечает (`GET /models`) |
| `make dump`       | дамп БД стенда в `dist/db/kodprozr-<дата>.sql.gz` (§9)                       |
| `make restore FILE=...` | пересоздаёт БД из дампа и перезапускает бэк и фронт (§9)              |
| `make offline-bundle` | офлайн-пакет для резервного ноутбука в `dist/offline/` (§9)             |
| `make offline-load` | загружает пакет на резервном ноутбуке; дальше `make reset OFFLINE=1` (§9) |
| `make video`      | видео-бэкап: Playwright-сценарий демо против стенда, видео в `dist/video/` (§9) |

`OFFLINE=1` у `up`, `reset`, `restore`, `llm-up` — без сборки образов и без обращений к registry
(`--no-build --pull never`), для резервного ноутбука после `make offline-load`.

**Сборка в сети хоста.** На машинах команды bridge-сеть Docker не выходит в интернет (VPN/TUN,
прокси: DNS отвечает, но TCP из контейнера висит), поэтому `npm ci` и `uv sync` при сборке
зависали — это и был сбой сборки 14.11. `make build` собирает в сети хоста: Compose 5 собирает
через `buildx bake`, а bake требует явного `--allow=network.host`, поэтому Makefile передаёт
описание сборки из `docker compose build --print` в `docker buildx bake --allow=network.host`.
Голый `docker compose build` по-прежнему собирает в bridge (`network: default`) и работает там,
где у контейнеров есть интернет. Вернуть обычную сборку и в make: `make build BUILD_NETWORK=default`.
Диагностика: `docker run --rm node:22-alpine wget -qO- -T 10 https://registry.npmjs.org/ >/dev/null`
висит, а с `--network host` проходит — значит, нужна сборка в сети хоста.

Команды бэка и фронта вынесены в переменные в начале `Makefile` (`MIGRATE_CMD`, `SEED_CMD`,
`BACK_TEST_CMD`, `BACK_LINT_CMD`, `FRONT_LINT_CMD`). Переопределить команду можно без правки файла:
`make seed SEED_CMD="python -m src.seed --dir data/example"`.

`precompute` и `eval` выполняются на хосте через `uv` и ходят в Postgres из compose на
`localhost:$POSTGRES_PORT` (`HOST_DB`). `data/generated` монтируется в бэкенд только на чтение.

Порядок перед демо: `make reset` → `make smoke` → `make reset` (smoke отправляет демо-обращение
и поднимает Соколова на 1-е место, а на показе это делается вживую).

Версии образов закреплены в `.env.example` (`POSTGRES_IMAGE`, `OLLAMA_IMAGE`) и в Dockerfile'ах
(`python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine`).

`make reset` снимает только том БД: раньше он вызывал `down -v` с профилем `llm` и заодно удалял том
`ollama_models` со скачанной моделью. Полный сброс вместе с моделями — только вручную:
`docker compose --profile llm down -v`.

## 4. Dev-режим

### Вариант A: код на хосте, Postgres в Docker (рекомендуется)

Перезапуск самый быстрый, и отладчик IDE работает без настройки.

```bash
docker compose up -d --wait postgres

# бэк (в .env или в shell: DATABASE_URL с localhost вместо postgres)
cd backend
uv sync
export DATABASE_URL=postgresql+asyncpg://kodprozr:kodprozr@localhost:5432/kodprozr
uv run alembic upgrade head
uv run uvicorn src.web.main:app --reload --port 8000   # путь к app сверить с backend/README.md

# фронт (во втором терминале)
cd frontend
npm ci
npm run dev        # http://localhost:5173, API из VITE_API_URL
```

### Вариант B: всё в Docker с hot reload

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
make up
```

Compose подхватывает override автоматически (файл в `.gitignore`). В этом режиме:

- исходники `backend/` смонтированы в `/app`, uvicorn запускается с `--reload`, а `.venv` образа
  сохраняется в анонимном томе;
- `frontend` заменяется на `node:22-alpine` с `npm run dev` на порту 5173.

Если в бэке появилась новая зависимость, пересоберите образ: `make build`. Чтобы вернуться в
prod-режим, удалите `docker-compose.override.yml`.

## 5. Локальная LLM (Ollama)

Бэк работает с LLM через OpenAI-совместимый API, Ollama отдаёт его на `/v1`. Без LLM
(`LLM_BASE_URL=` пусто) разбор обращений, докладная и ассистент работают на правилах и шаблонах.
Есть три варианта подключения, ниже они идут от простого к сложному.

| Вариант | `LLM_BASE_URL` в `.env` | Когда выбирать |
| --- | --- | --- |
| А. Ollama в compose (`make llm-up`) | `http://ollama:11434/v1` | чистая машина, демо-ноутбук, VPS |
| Б. Ollama на хосте, бэк в Docker | `http://host.docker.internal:11434/v1` | Ollama уже стоит на хосте и работает на GPU |
| В. Общая LLM команды | `http://<ip>:11434/v1` или через SSH-туннель | своей машине не хватает памяти или GPU |

Во всех вариантах `LLM_API_KEY=ollama` (Ollama принимает любую непустую строку) и
`LLM_MODEL=qwen2.5:7b-instruct`. После правки `.env` перезапустите бэк командой `make up` и
проверьте подключение: `make llm-check` выполняет `GET /models` из контейнера backend с таймаутом 5 с.

### Вариант А: Ollama в compose

```bash
make llm-up            # ollama из профиля llm, ollama pull $LLM_MODEL, прогрев
```

`make llm-up` сам выбирает GPU. Если `docker info` показывает runtime `nvidia`, к compose
подключается `docker-compose.gpu.yml`; иначе Ollama работает на CPU, и команда пишет об этом.
Режим задаётся явно через `LLM_GPU=1` или `LLM_GPU=0`. Для GPU на хосте нужен
nvidia-container-toolkit: драйвера NVIDIA для контейнера мало. С `-f docker-compose.gpu.yml`
compose не подхватывает `docker-compose.override.yml`, поэтому для dev-режима с GPU файлы
перечисляются явно.

Если на хосте уже работает своя Ollama на 11434, порт контейнера сдвиньте: `OLLAMA_PORT=11435`.
Бэк ходит к контейнеру по имени `ollama:11434`, поэтому хост-порт на него не влияет.

Проверка с хоста:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:7b-instruct","messages":[{"role":"user","content":"Привет"}]}'
```

Модели хранятся в томе `ollama_models` и при пересоздании контейнера заново не скачиваются.
`make reset` этот том не трогает. Удалить его можно только вручную: `docker compose --profile llm down -v`.

### Вариант Б: Ollama на хосте, бэк в Docker

Подходит, когда Ollama установлена на хосте и видит GPU сама, без nvidia-container-toolkit.
Именно так устроена машина, где проверялся этот документ: Ollama 0.12.6 на GPU,
`127.0.0.1:11434`, модель `qwen2.5:7b-instruct`, runtime `nvidia` в Docker отсутствует.

У бэка в compose уже есть `extra_hosts: host.docker.internal:host-gateway`, поэтому имя
`host.docker.internal` указывает на шлюз docker-сети (обычно `172.17.0.1`). Чтобы бэк
достучался до Ollama, нужны ещё два условия:

1. **Ollama слушает не только loopback.** По умолчанию она принимает соединения только на
   `127.0.0.1:11434`. Для systemd-сервиса задайте адрес так:
   `sudo systemctl edit ollama` → `[Service]` / `Environment="OLLAMA_HOST=0.0.0.0"` →
   `sudo systemctl restart ollama`. Если Ollama запускается вручную, то так:
   `OLLAMA_HOST=0.0.0.0 ollama serve`. У Ollama нет авторизации, поэтому в недоверенной сети
   порт 11434 должен быть закрыт файрволом снаружи.
2. **Файрвол хоста пропускает docker-сети к порту 11434.** Например, для iptables:
   `sudo iptables -I INPUT -s 172.16.0.0/12 -p tcp --dport 11434 -j ACCEPT`, для ufw:
   `sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp`.

Проверка: `make llm-check` должен вывести список моделей. Если ответ — «Connection refused»,
Ollama слушает только `127.0.0.1` (условие 1). Если ответа нет до таймаута, пакеты отбрасывает
файрвол (условие 2). На проверочной машине 15.11 было именно так: из контейнера backend
`host.docker.internal:11434` давал timeout, а не отказ.

**Таймаут при файрволе с DROP.** Если файрвол отбрасывает пакеты молча, бэк не получает
отказа соединения. Установку соединения ограничивает `LLM_CONNECT_TIMEOUT_SECONDS` (по умолчанию
5 с, B-20, #34): по его истечении бэк без повтора уходит на фоллбэк. До B-20 бэк ждал весь
`LLM_TIMEOUT_SECONDS` с повтором, до 180 с на обращение. Проверка 15.11 на адресе с DROP:
`POST /appeals` ответил за 2,9 с, `/assistant/ask` за 2,0 с (connect-timeout 2 с). Модель всё
равно не используется, поэтому включайте LLM, только когда `make llm-check` показывает модели.

### Вариант В: общая LLM команды

Одна машина с GPU раздаёт модель остальным.

- **SSH-туннель (рекомендуется).** Ollama на раздающей машине остаётся на `127.0.0.1`, у
  участника выполняется `ssh -N -L 11434:127.0.0.1:11434 <user>@<машина-с-llm>`. Если бэк
  запущен на хосте (dev-режим А, §4), укажите `LLM_BASE_URL=http://localhost:11434/v1`. Если бэк
  в Docker, туннель должен слушать адрес, доступный из контейнера:
  `ssh -N -L 172.17.0.1:11434:127.0.0.1:11434 ...`, и `LLM_BASE_URL=http://host.docker.internal:11434/v1`.
  Файрвол при этом должен пропускать docker-сети, как в варианте Б.
- **Открытый порт в доверенной сети.** Для Ollama из compose задайте `OLLAMA_BIND_HOST=0.0.0.0`
  и выполните `make llm-up`. Для Ollama на хосте задайте `OLLAMA_HOST=0.0.0.0`. У участников
  `LLM_BASE_URL=http://<ip-машины>:11434/v1`. Авторизации нет, поэтому только в своей сети.

Оба способа общей LLM вживую не проверялись: вторая машина команды была недоступна.

### Ресурсы и модель

- `qwen2.5:7b-instruct` весит около 4.7 ГБ и требует около 8 ГБ RAM, на GPU — около 5 ГБ VRAM
  (Q4). На CPU ответ занимает от нескольких до десятков секунд: для предрасчёта приемлемо, для
  живого показа медленно (порог решения — [demo.md](demo.md)).
- **Замер 16.11, вариант А на CPU** (runtime `nvidia` в Docker нет, `ollama ps` → `100% CPU`,
  модель прогрета `make llm-up`): `make smoke` проходит, 50 проверок, но первое демо-обращение
  `POST /appeals` упёрлось в `LLM_TIMEOUT_SECONDS=90` и ушло на фоллбэк (90,4 с). Повторный
  разбор того же текста (`reanalyze`, `engine=llm`) занял 26,3 с, `/assistant/ask` — 30,6 с.
  Порог живого показа 20 с не выполняется ни в одном случае. Вывод: на демо LLM включаем только
  на GPU (вариант А с nvidia-container-toolkit или вариант Б). Без GPU показываем фоллбэк.
  Докладная от LLM не зависит: `TemplateReportWriter` (AI-09 выключен), ответ за 11 мс.
- **Замер 16.11, вариант А на GPU** на той же машине (RTX 4060 Ti 8 ГБ, драйвер 615.78) после
  `sudo pacman -S nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker
  && sudo systemctl restart docker`. `make llm-up` сам подключил `docker-compose.gpu.yml`,
  `ollama ps` → `100% GPU`, VRAM 6,5 ГБ. `make smoke` → 50 проверок: демо-обращение 5,4 с
  (`engine=llm`), `reanalyze` 4,2 с, `/assistant/ask` 1,0 с. Порог 20 с выполняется с запасом.
  Перезапуск Docker останавливает все контейнеры: без `restart: unless-stopped` они сами не встают.
- **Модель без сети.** Если контейнер не достаёт `registry.ollama.ai` (16.11 `ollama pull` из
  docker-сети упал по `i/o timeout`), а на хосте модель уже есть в `~/.ollama/models`, её можно
  скопировать в том: `docker run --rm -v kodprozr_ollama_models:/v -v ~/.ollama/models:/src:ro
  alpine:3 sh -c 'mkdir -p /v/models && cp -r /src/blobs /src/manifests /v/models/'`, затем
  `make llm-up`.
- На слабом ноутбуке подойдёт `qwen2.5:3b-instruct` (около 2 ГБ): поменяйте `LLM_MODEL` и
  снова выполните `make llm-up`.
- Тег образа закреплён: `OLLAMA_IMAGE=ollama/ollama:0.12.6`. На этой версии AI-03 прогоняет
  модель. Последняя стабильная версия на 15.11 — 0.40.16. Переходить на неё стоит только после
  прогона `make llm-up` и `make eval EVAL_ARGS="--llm --limit 30"` на новой версии.
- `LLM_TIMEOUT_SECONDS=90`: 7B на CPU отвечает десятки секунд, фронт ждёт до 150 с. При
  недоступной LLM бэк уходит на фоллбэк через `LLM_CONNECT_TIMEOUT_SECONDS` (5 с), даже если
  файрвол молча отбрасывает пакеты; демо не встаёт.
- Облачный провайдер или vLLM подключается без изменений в коде: поменяйте `LLM_BASE_URL`,
  `LLM_API_KEY` и `LLM_MODEL`.

## 6. Деплой демо на один VPS

Целевая схема: на VPS работает docker compose, все порты слушают только `127.0.0.1`. Наружу открыт
Caddy на хосте: он получает HTTPS-сертификат Let's Encrypt и раздаёт фронт и API с одного домена.

```
интернет :443 ──► Caddy ──► /api/*, /health, /docs, /openapi.json ──► 127.0.0.1:8000 (backend)
                         └► всё остальное ─────────────────────────► 127.0.0.1:3000 (frontend)
```

Ресурсы VPS: без LLM хватит 2 vCPU и 4 ГБ RAM. С локальной `qwen2.5:7b` на CPU нужно от 4 vCPU и
12–16 ГБ RAM. Другой вариант — облачный LLM endpoint.

### Шаги

```bash
# 1. Docker + Caddy (Ubuntu 24.04)
curl -fsSL https://get.docker.com | sh
sudo apt install -y caddy make git
sudo ufw allow 22,80,443/tcp && sudo ufw enable

# 2. Код
git clone <repo> /opt/kodprozr && cd /opt/kodprozr
cp .env.example .env
```

Поправьте `.env` для стенда (вместо `demo.example.ru` укажите свой домен):

```
POSTGRES_PASSWORD=<длинный случайный>
DATABASE_URL=postgresql+asyncpg://kodprozr:<тот же пароль>@postgres:5432/kodprozr
CORS_ORIGINS=https://demo.example.ru
VITE_API_URL=/api/v1
AUTH_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(48))">
AUTH_COOKIE_SECURE=true
SMOKE_USERNAME=smoke
SMOKE_PASSWORD=<длинный случайный, не меньше 12 символов>
BIND_HOST=127.0.0.1
```

Пользователей создайте в контейнере бэка ([auth.md](auth.md)): рабочих —
`docker compose run --rm backend python -m src.core.infrastructure.create_user <логин>`,
учётку для smoke релизов — с паролем из `.env`:

```bash
# .env хоста попадает в контейнер через env_file, пароль не светится в аргументах.
docker compose run --rm backend sh -c \
  'python -m src.core.infrastructure.create_user "$SMOKE_USERNAME" --password-env SMOKE_PASSWORD'
```

Без `SMOKE_USERNAME`/`SMOKE_PASSWORD` в `.env` хоста `deploy.sh deploy` и `rollback`
останавливаются до выкладки: бизнес-API требует входа, и smoke без учётки получил бы 401.

`BIND_HOST=127.0.0.1` обязателен: Docker публикует порты в обход ufw, и без этой настройки
сервисы окажутся доступны из интернета напрямую.

```bash
# 3. Запуск и данные
make up && make seed
make llm-up            # если LLM локальная
```

`/etc/caddy/Caddyfile`:

```caddyfile
demo.example.ru {
    encode zstd gzip

    # Необязательно: закрыть демо паролем. Хэш: caddy hash-password
    # basic_auth {
    #     jury <bcrypt-хэш>
    # }

    @api path /api/* /health /docs /docs/* /openapi.json
    handle @api {
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```

```bash
sudo systemctl reload caddy
curl -fsS https://demo.example.ru/health      # {"status":"ok"}
```

DNS: A-запись домена указывает на IP VPS. Caddy выпускает сертификат сам при первом запросе;
для этого порты 80 и 443 должны быть открыты.

Если вместо Caddy используется nginx: те же два `location` (`/api/` и `/` с `proxy_pass` на
127.0.0.1:8000 и :3000), сертификат выпускается командой `sudo certbot --nginx -d demo.example.ru`.

### Обновление и бэкап

Штатное обновление прода — релизный тег (раздел 7): образы из GHCR, бэкап перед миграциями,
health/smoke и откат. Ручной вариант ниже подходит для резервного ноутбука или для стенда,
где конвейер ещё не настроен.

```bash
cd /opt/kodprozr
make dump                       # бэкап перед обновлением: dist/db/kodprozr-<дата>.sql.gz
git pull && make up             # пересборка и перезапуск; миграции применятся при старте
```

Восстановление: `make restore FILE=dist/db/kodprozr-<дата>.sql.gz`. Цель пересоздаёт БД
(`dropdb --force` + `createdb`), заливает дамп и поднимает бэк и фронт. Подробнее — §9.
Дампы кладите и вне VPS: `scp <vps>:/opt/kodprozr/dist/db/*.sql.gz .`.

## 7. Релиз и деплой

Production выкладывается только по релизному тегу. Push в рабочие ветки, в `dev` и в `main`
деплой не запускает: `release.yml` слушает только теги, `ci.yml` деплоя не содержит.

```
PR → dev ──► релизный PR dev → main (merge commit) ──► sync-dev.yml: служебный PR main → dev
                                   │
                    тег vX.Y.Z на коммите main
                                   ▼
release.yml: verify ─► checks (ci.yml) ─► images (GHCR) ─► deploy (environment production)
             тег в main?   backend/frontend/data   backend, frontend   ssh: pull, бэкап, migrate,
                                                                       up, health, smoke, откат
```

### Workflow

| Файл | Триггер | Что делает |
| --- | --- | --- |
| `.github/workflows/ci.yml` | PR и push в `dev`/`main`, `workflow_call` | проверки `backend`, `frontend`, `data`; без деплоя |
| `.github/workflows/release.yml` | push тега `v*.*.*` или `demo-v*` | релизный конвейер, см. ниже |
| `.github/workflows/sync-dev.yml` | push в `main`, ручной запуск | служебный PR `main → dev` |
| `.github/workflows/workflow-policy.yml` | PR в `dev`/`main` | проверка `policy`: ветка, issue, сообщения |

Задания `release.yml`:

1. **verify.** Тег должен иметь вид `vMAJOR.MINOR.PATCH` или `demo-vN`, а его коммит должен быть
   достижим из `origin/main` (`git merge-base --is-ancestor`). Иначе релиз падает здесь, до сборки
   и до деплоя. Тег на коммите из `dev` или рабочей ветки отклоняется.
2. **checks.** Вызывает `ci.yml` через `workflow_call`, то есть те же проверки, что и в PR.
3. **images.** Собирает и публикует `ghcr.io/<owner>/<repo>/backend:<tag>` и
   `ghcr.io/<owner>/<repo>/frontend:<tag>` (имя в нижнем регистре, сейчас
   `ghcr.io/avt0b/kod_prozr_2026/...`). Используется `GITHUB_TOKEN` с `packages: write`.
   `VITE_API_URL` фронта берётся из переменной `PROD_VITE_API_URL` и по умолчанию равен `/api/v1`,
   потому что на стенде фронт и API находятся за одним доменом (раздел 6).
4. **deploy.** Выполняется только для тегов `v*` (тег `demo-vN` публикует снимок образов без
   деплоя, см. workflow.md) и только в environment `production`. Если секреты `DEPLOY_HOST`,
   `DEPLOY_USER` или `DEPLOY_SSH_KEY` не заданы, job пишет notice «Deploy пропущен» и
   завершается успешно, релиз при этом остаётся зелёным. Если секреты заданы, по ssh на хост
   копируются `docker-compose.yml`, `deploy/`, `scripts/smoke.py` и `data/generated` в
   `DEPLOY_PATH`, после чего запускается `deploy/deploy.sh deploy <tag> <prefix> <actor>`.

Один релиз выполняется за раз (`concurrency: release`), начатый деплой не отменяется.

### Environment, секреты и переменные

Значения задаются в **Settings → Environments → `production`**. В репозиторий, issues и
handoff-файлы они не попадают. В логе Actions секреты маскируются, а workflow проверяет только,
заданы ли они, и их не печатает. Токен GHCR передаётся `deploy.sh` через stdin, после выкладки
выполняется `docker logout`.

| Имя | Тип | Обязателен | Назначение |
| --- | --- | --- | --- |
| `DEPLOY_HOST` | secret | да | адрес VPS |
| `DEPLOY_USER` | secret | да | ssh-пользователь, входит в группу `docker` |
| `DEPLOY_SSH_KEY` | secret | да | приватный ключ (ed25519) только для деплоя, без пароля |
| `DEPLOY_KNOWN_HOSTS` | secret | рекомендуется | строка `ssh-keyscan` хоста; без неё ключ хоста принимается без проверки (warning) |
| `DEPLOY_PORT` | variable | нет | порт ssh, по умолчанию `22` |
| `DEPLOY_PATH` | variable | нет | каталог деплоя на хосте, по умолчанию `/opt/kodprozr` |
| `PROD_VITE_API_URL` | variable (repo) | нет | адрес API для бандла фронта, по умолчанию `/api/v1` |
| `DEPLOY_SEED` | variable | нет | `true` — залить `data/generated` после миграций; только для первого деплоя на пустую БД |
| `DEPLOY_SMOKE_ARGS` | variable | нет | аргументы `smoke.py`, по умолчанию `--keep-demo` |
| `SYNC_PR_TOKEN` | secret (repo) | нет | fine-grained PAT (Contents: read, Pull requests: write) для служебного PR, чтобы на нём сразу стартовали CI и policy |

`PROD_VITE_API_URL` — переменная уровня репозитория, потому что job `images` работает без
environment. Остальные значения можно хранить в environment. Если тариф не даёт environment
для приватного репо, те же имена работают и как секреты/переменные репозитория.

Настройка владельцем (значения подставляются локально и в git не попадают):

```bash
REPO=avt0b/kod_prozr_2026
# environment: деплой разрешён только с тегов v*.*.*
gh api -X PUT "repos/$REPO/environments/production" --input - <<'JSON'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api -X POST "repos/$REPO/environments/production/deployment-branch-policies" \
  -f name='v*.*.*' -f type=tag
# Required reviewers (по желанию) включаются в Settings → Environments → production.

ssh-keygen -t ed25519 -N '' -C kodprozr-deploy -f ./deploy_key   # публичную часть — в authorized_keys хоста
gh secret set DEPLOY_SSH_KEY --env production --repo "$REPO" < ./deploy_key
gh secret set DEPLOY_HOST --env production --repo "$REPO"        # значение вводится интерактивно
gh secret set DEPLOY_USER --env production --repo "$REPO"
ssh-keyscan -t ed25519 <хост> | gh secret set DEPLOY_KNOWN_HOSTS --env production --repo "$REPO"
gh variable set PROD_VITE_API_URL --repo "$REPO" --body /api/v1
rm ./deploy_key
```

### Подготовка хоста

Хост готовится по разделу 6: Docker, Caddy, ufw, DNS. Вместо `git clone` достаточно каталога
`DEPLOY_PATH` с `.env`, остальные файлы туда кладёт релиз. Если в каталоге уже лежит клон
репозитория, релиз перезапишет `docker-compose.yml` версией из тега. Требования:

- `.env` стенда лежит в `DEPLOY_PATH`, без него `deploy.sh` откажется работать;
- `DEPLOY_USER` состоит в группе `docker`, на хосте есть `python3` и `curl` (Ubuntu 24.04 — есть);
- первый деплой на пустую БД выполняется с переменной `DEPLOY_SEED=true`; после успеха её надо
  удалить, иначе сиды будут заливаться при каждом релизе.

### Что делает `deploy/deploy.sh`

`deploy.sh deploy <tag> <prefix> [<user>]` выполняет шаги по порядку:

1. Входит в GHCR, если токен передан на stdin.
2. Скачивает образы `<prefix>/{backend,frontend}:<tag>` и поднимает `postgres`.
3. Снимает дамп `backups/pre-<tag>-<время>.sql.gz` и выполняет `alembic upgrade head`.
4. Поднимает `backend` и `frontend` с `--wait` по healthcheck.
5. Проверяет `GET /health` и запускает `python3 scripts/smoke.py --api http://127.0.0.1:8000 --keep-demo`
   под учёткой `SMOKE_USERNAME`/`SMOKE_PASSWORD` из `.env` хоста.

Образы подставляет наложение `deploy/docker-compose.release.yml`, в него передаются
`BACKEND_IMAGE` и `FRONTEND_IMAGE`. Локальный `make up` это наложение не использует и по-прежнему
собирает образы сам.

Smoke с `--keep-demo` не отправляет демо-обращение, но выполняет `risk/recompute` и создаёт одну
докладную. Это записи журнала, данные демо при этом не ломаются. Для smoke нужна залитая
синтетика.

Состояние релизов хранится в `DEPLOY_PATH/.release/`: `current_tag` (текущий успешный),
`previous_tag`, `image_prefix` и `history.log`.

### Откат

- **Автоматический.** Если health или smoke нового тега не прошли, `deploy.sh` поднимает
  `previous_tag` теми же шагами (без нового бэкапа и сидов), записывает исход в `history.log`
  и завершается с ошибкой. Job `deploy` и релиз становятся красными, `current_tag` при этом
  не меняется.
- **Ручной на хосте**, если проблема всплыла после успешного релиза:

  ```bash
  cd /opt/kodprozr
  deploy/deploy.sh status      # текущий/предыдущий тег, контейнеры, история
  deploy/deploy.sh rollback    # поднять previous_tag; current и previous меняются местами
  ```

  Без входа в GHCR используются уже скачанные образы. Если образа на хосте нет, сначала
  выполните `docker login ghcr.io` (PAT с `read:packages`).
- **Через Actions.** Можно перезапустить (Re-run all jobs) релиз прошлого тега. Новый тег на
  старом коммите не нужен.
- **Миграции не откатываются.** Если новая миграция несовместима со старым кодом, после отката
  восстановите дамп, снятый перед ней:

  ```bash
  cd /opt/kodprozr
  docker compose stop backend frontend
  docker compose exec -T postgres psql -U kodprozr -d kodprozr \
    -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  gunzip -c backups/pre-<tag>-<время>.sql.gz \
    | docker compose exec -T postgres psql -U kodprozr -d kodprozr -v ON_ERROR_STOP=1
  docker compose start backend frontend   # те же контейнеры текущего (откатанного) тега
  ```

  Поэтому миграции пишем обратно совместимыми: в одном релизе столбец или таблицу добавляем,
  а удаляем только в следующем.

### Выпуск релиза (Кирилл)

```bash
git fetch origin
git switch --detach origin/main            # проверенный коммит после релизного PR dev → main
git tag -a v1.0.0 -m 'Релиз v1.0.0'
git push origin v1.0.0                     # запускает release.yml
gh run watch "$(gh run list --workflow Release --limit 1 --json databaseId --jq '.[0].databaseId')"
```

Тег ставится только после merge релизного PR и зелёного CI на `main`. Тег `demo-vN` ставится так же,
он публикует образы, но не деплоит.

### Синхронизация main → dev

После каждого push в `main` (merge релизного PR) `sync-dev.yml` проверяет, содержит ли `dev` уже
`main`. Если нет и служебный PR ещё не открыт, workflow открывает PR `main → dev`. Номер release
issue он берёт из строки `Issue: #N` релизного PR. Сам workflow ничего не пушит; PR сливается
обычным **merge commit** после CI и ревью. Squash и rebase не подходят: после них `main` не станет
предком `dev`, и PR откроется снова.

- Чтобы `GITHUB_TOKEN` мог открыть PR, владелец включает **Settings → Actions → General →
  Workflow permissions → Allow GitHub Actions to create and approve pull requests**
  (`gh api -X PUT repos/$REPO/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true`).
- PR, открытый `GITHUB_TOKEN`, сам CI не запускает. Есть два способа: задать секрет `SYNC_PR_TOKEN`
  или после открытия закрыть и снова открыть PR (это запустит CI и policy). Policy можно также
  запустить отдельно: **Actions → Workflow policy → Run workflow**, `pr=<номер>`.

### Защита веток (включает владелец репозитория вручную)

Workflow настройки репозитория не меняют. Защиту `main` и `dev` включает владелец (`avt0b`), когда
проверки `backend`, `frontend` (workflow `CI`) и `policy` (workflow `Workflow policy`) уже хотя бы
раз прошли на PR. До первого запуска GitHub не предлагает их в списке required checks.

Branch protection и rulesets для **приватного** репозитория требуют тарифа GitHub Pro/Team
(для личного аккаунта владельца — Pro). На Free настройки ниже вернут 403; тогда репозиторий
нужно сделать публичным или сменить тариф.

**Через UI**: Settings → Branches → Add branch ruleset (или Add classic branch protection rule)
для `main` и отдельно для `dev`:

1. Branch name pattern: `main` (затем `dev`).
2. Require a pull request before merging; Required approvals: 1; Dismiss stale approvals.
3. Require status checks to pass: `backend`, `frontend`, `policy`. Для `main` также включить
   Require branches to be up to date.
4. Require conversation resolution before merging.
5. Do not allow bypassing the above settings (Include administrators).
6. Allow force pushes и Allow deletions оставить **выключенными**.
7. Для `main` в Settings → General → Pull Requests оставить включённым Allow merge commits,
   потому что релиз и синхронизация идут merge commit.

**Через `gh api`** (classic branch protection, выполняет владелец):

```bash
REPO=avt0b/kod_prozr_2026
protect() {  # $1 — ветка, $2 — strict (true: ветка должна быть актуальна перед merge)
  gh api -X PUT "repos/$REPO/branches/$1/protection" \
    -H 'Accept: application/vnd.github+json' --input - <<JSON
{
  "required_status_checks": {
    "strict": $2,
    "checks": [{"context": "backend"}, {"context": "frontend"}, {"context": "policy"}]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
}
protect main true
protect dev false

# проверка
gh api "repos/$REPO/branches/main/protection" \
  --jq '{checks: [.required_status_checks.checks[].context], reviews: .required_pull_request_reviews.required_approving_review_count, admins: .enforce_admins.enabled, force: .allow_force_pushes.enabled, delete: .allow_deletions.enabled}'
```

Если проверка `backend` или `frontend` пропущена (каталога ещё нет и `detect` вернул `false`),
GitHub считает её успешной. Это ожидаемо.

Дополнительно можно запретить ставить и удалять релизные теги всем, кроме владельца
(ruleset для тегов):

```bash
gh api -X POST "repos/$REPO/rulesets" --input - <<'JSON'
{
  "name": "release-tags",
  "target": "tag",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/tags/v*.*.*"], "exclude": []}},
  "rules": [{"type": "creation"}, {"type": "update"}, {"type": "deletion"}],
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]
}
JSON
```

`actor_id: 5` — роль Admin репозитория: только она может ставить и двигать теги `v*.*.*`.
Если релизы ставит Кирилл без прав Admin, выдайте ему роль Maintain и добавьте в
`bypass_actors` запись `{"actor_id": 2, "actor_type": "RepositoryRole", "bypass_mode": "always"}`.

## 8. Чеклист Кирилла (10–13 ноября)

### День 1 — 10.11: локальный стек

- [ ] Влить корневую инфраструктуру: compose, Makefile, CI, pre-commit, `.env.example`.
- [ ] Когда каркасы будут готовы, сверить допущения с `backend/README.md` и `frontend/`:
  - [ ] команда миграций: `alembic upgrade head`, venv образа в `PATH`;
  - [ ] путь к приложению (`BACKEND_APP`, по умолчанию `src.web.main:app`);
  - [ ] команда сида (`SEED_CMD`, по умолчанию `python -m src.seed`);
  - [ ] в `frontend/Dockerfile` есть `ARG VITE_API_URL` и nginx с `try_files ... /index.html` для SPA-роутинга;
  - [ ] в `frontend/package.json` есть скрипты `lint`, `build`, `dev`, а `package-lock.json` закоммичен;
  - [ ] в образе бэка есть `/health`, а образ собирается без dev-зависимостей.
- [ ] `make up` на чистой машине: все сервисы `healthy` в `make ps`, фронт открывается, запросы к API без ошибок CORS.
- [ ] CI зелёный на `dev` и `main`; защита обеих веток требует PR, ревью и успешные проверки `backend`, `frontend`, `policy` (см. workflow.md).
- [ ] `pre-commit install` выполнен у всей команды.

### День 2 — 11.11: стенд

- [ ] VPS, домен, DNS, Caddy с HTTPS, `.env` стенда с нормальным паролем БД.
- [ ] `make up && make seed` на стенде, проверка `https://<домен>/health` и основных экранов.
- [ ] Решить вопрос LLM: локальная Ollama на стенде или облачный endpoint. Замерить время анализа одного обращения.
- [ ] Скачать модель заранее (`make llm-up`) и закрепить версию `OLLAMA_IMAGE` вместо `latest`.
- [ ] Сделать первый `pg_dump` с сидом и сохранить его вне VPS.
- [ ] Кирилл описывает релизный конвейер `dev → main → тег vMAJOR.MINOR.PATCH → deploy`, проверку принадлежности тега `main`, secrets, health/smoke и откат; ручные команды не обходят релизный процесс.

### День 3 — 12.11: фриз и запасной план

- [ ] Code freeze вечером; после него — только фиксы демо-сценария.
- [ ] Дважды прогнать демо-сценарий на стенде: с телефона, из другой сети, в режиме инкогнито.
- [ ] Запасной вариант: ноутбук докладчика с офлайн-пакетом, моделью и дампом БД (§9). Он должен работать без интернета.
- [ ] Проверить, что после `docker compose restart` и перезагрузки VPS всё поднимается само (`restart: unless-stopped`).
- [ ] Проверить, что README и этот документ актуальны и ссылки работают.

### 13.11 — сдача

- [ ] Утром проверить `/health`, `make ps`, логи без ошибок, свободное место на диске (`df -h`).
- [ ] Ничего не деплоить после финального прогона.

## 9. Резервный ноутбук без сети, дамп, видео

Резерв на защиту (OPS-07, OPS-08) состоит из трёх частей: дампа БД, офлайн-пакета для второго
ноутбука и видео демо. Все артефакты складываются в `dist/`, который не попадает в git.

### Дамп и восстановление БД

```bash
make dump                                        # dist/db/kodprozr-<дата>.sql.gz
make restore FILE=dist/db/kodprozr-<дата>.sql.gz # пересоздать БД из дампа
```

`make dump` вызывает `pg_dump --no-owner --no-privileges` в контейнере postgres; при ошибке
недописанный файл удаляется. `make restore` поднимает postgres, останавливает бэк и фронт,
пересоздаёт БД, заливает дамп с `ON_ERROR_STOP` и поднимает стек обратно. Дамп содержит и
`alembic_version`, поэтому миграции при старте бэка ничего не меняют, если дамп снят с той же
версии кода.

Проверено 15.11. Порядок: `make reset`, `make dump` (296 КБ), `docker compose down -v`,
`make up OFFLINE=1` (пустая БД после миграций), `make restore FILE=... OFFLINE=1` (30 с),
`make smoke`. Число строк во всех 16 таблицах и контрольная сумма `risk.scores` до и после
совпали, результат `smoke: OK, 45 проверок`.

### Офлайн-пакет для резервного ноутбука

На подготовленной машине с интернетом и собранным стеком:

```bash
make build && make reset && make dump    # свежие образы и дамп «как перед демо»
make offline-bundle                      # dist/offline/
# Модель с Ollama на хосте (вариант Б из §5), а не из тома compose:
make offline-bundle OLLAMA_MODELS_DIR=$HOME/.ollama/models
```

В `dist/offline/` попадает:

| Файл | Содержимое |
| --- | --- |
| `images/kodprozr.tar.gz` | `kodprozr-backend:local`, `kodprozr-frontend:local`, `POSTGRES_IMAGE` |
| `images/ollama.tar.gz` | `OLLAMA_IMAGE`, если образ скачан (`WITH_OLLAMA=auto\|1\|0`) |
| `models/ollama-models.tar` | модели из тома `kodprozr_ollama_models` или из `OLLAMA_MODELS_DIR` (`WITH_MODELS=auto\|1\|0`) |
| `env/.env` | `.env` машины, где собран пакет (или `.env.example`) |
| `db/*.sql.gz` | последний дамп из `dist/db/` |
| `kodprozr-src.tar.gz` | `git archive HEAD`: compose, Makefile, `data/generated`; незакоммиченных правок в нём нет |
| `MANIFEST.txt`, `SHA256SUMS` | коммит, id образов, модель; контрольные суммы |

Каталог копируется на резервный ноутбук целиком (флешка, `rsync`). На ноутбуке нужны Docker с
Compose, `make` и `python3`, интернет не нужен:

```bash
mkdir kodprozr && tar -xzf <пакет>/kodprozr-src.tar.gz -C kodprozr && cd kodprozr
make offline-load OFFLINE_DIR=<пакет>   # sha256, docker load, модели в том, .env из пакета
make reset OFFLINE=1                    # стек, миграции, сиды — без сборки и без registry
make smoke && make reset OFFLINE=1      # проверка и возврат к состоянию «перед демо»
make llm-up OFFLINE=1                   # если демо идёт с LLM (модель из пакета)
```

`OFFLINE=1` передаёт compose `--no-build --pull never`. Если какого-то образа нет, команда
сразу падает и не пытается ничего скачать. Если на ноутбуке уже есть `.env`, `offline-load`
его не перезаписывает. Порты и `VITE_API_URL` в пакете взяты с машины сборки, а
`VITE_API_URL` уже вшит в образ фронта, поэтому на резервном ноутбуке порт бэка должен
быть тем же.

Проверено 15.11 на машине сборки (второго ноутбука не было), пакет занял 6.5 ГБ, из них
модель 4.4 ГБ и образ Ollama 1.9 ГБ. Сборка пакета заняла 1.5 мин. Затем:

- образы `kodprozr-backend:local` и `kodprozr-frontend:local` удалены;
- исходники распакованы из `kodprozr-src.tar.gz` в пустой каталог;
- `make offline-load` (1 мин): контрольные суммы сошлись, образы загружены с теми же id, что в
  `MANIFEST.txt`, модель в томе;
- `make reset OFFLINE=1` (37 с), `make smoke`: `OK, 45 проверок`;
- Ollama из пакета поднята на `OLLAMA_PORT=11435`: `ollama list` показал `qwen2.5:7b-instruct`.

Не проверено: отключение сети целиком (машина сборки оставалась в сети, отсутствие загрузок
обеспечивал `--pull never`) и прогрев модели в `make llm-up OFFLINE=1`. Прогрев 7B на CPU в
контейнере требует около 8 ГБ свободной RAM, а на проверочной машине их не было.
На репетиции нужно пройти этот сценарий на реальном резервном ноутбуке.

### Видео-бэкап демо

```bash
make reset          # видео пишется с чистого стенда
make video          # Playwright-сценарий demo.md, видео в dist/video/demo-<дата>-N.webm
make reset          # сценарий отправляет демо-обращение — вернуть стенд
```

`make video` запускает `frontend/e2e/demo.spec.ts` с `DEMO_VIDEO=1` (запись 1920×1080),
`DEMO_SLOWMO=400`, `BASE_URL=$FRONT_URL` и `API_URL=$API_URL/api/v1`, порты берутся из `.env`.
Записанные `.webm` копируются в `dist/video/`. Если сценарий упал, частичное видео всё равно
сохраняется, а код выхода остаётся ненулевым. Нужны `cd frontend && npm ci && npx playwright
install chromium`.

**Зависимость от #23.** Сценарий `frontend/e2e/demo.spec.ts` и `frontend/playwright.config.ts`
приходят из ветки #23 (зона фронта) и в `dev` ещё не влиты. До их слияния `make video` сразу
завершается понятной ошибкой «Нет frontend/e2e/demo.spec.ts…». Переменные сверены с
`playwright.config.ts` из ветки #23, а запись видео целиком после слияния #23 не проверялась.

Готовое видео и дамп храните в двух местах: на обоих ноутбуках и на флешке (чеклист в
[demo.md](demo.md)).
