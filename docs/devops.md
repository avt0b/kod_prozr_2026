# DevOps: запуск, dev-режим, LLM, деплой

Ответственный — Кирилл. Срок сдачи — 13 ноября 2026. Порты и переменные задаёт
[contracts.md](contracts.md); если они меняются, этот файл обновляется вместе с ним.

## 1. Схема сервисов

```
                    браузер
             │                    │
   :3000 (prod) / :5173 (dev)    :8000  VITE_API_URL=http://localhost:8000/api/v1
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
| `postgres` | `postgres:16-alpine`          | 5432             | `postgres:5432`  | `pg_isready`                   |
| `backend`  | `./backend/Dockerfile`        | 8000             | `backend:8000`   | `GET /health` → 200            |
| `frontend` | `./frontend/Dockerfile`       | 3000 (dev: 5173) | `frontend:80`    | `GET /` → 200                  |
| `ollama`   | `ollama/ollama` (профиль llm) | 11434            | `ollama:11434`   | `ollama list`                  |

Порядок старта: `postgres` (healthy) → `backend` (сначала `alembic upgrade head`, затем uvicorn) →
`frontend`. Порты публикуются на `BIND_HOST` (по умолчанию `127.0.0.1`).

Браузер обращается к API напрямую по `VITE_API_URL`, nginx фронта ничего не проксирует. Поэтому
бэк должен разрешать origin фронта в `CORS_ORIGINS`. На VPS оба сервиса стоят за одним доменом
(раздел 6), и CORS там не участвует.

## 2. Переменные окружения

Все переменные лежат в одном `.env` в корне репо (шаблон — `.env.example`). Docker Compose
подставляет их в `docker-compose.yml`, контейнер `backend` получает их через `env_file`.

| Переменная                       | Кто читает        | По умолчанию / пример                                           |
| -------------------------------- | ----------------- | --------------------------------------------------------------- |
| `POSTGRES_USER/PASSWORD/DB`      | postgres          | `kodprozr` / `kodprozr` / `kodprozr`                            |
| `DATABASE_URL`                   | backend           | `postgresql+asyncpg://kodprozr:kodprozr@postgres:5432/kodprozr` |
| `CORS_ORIGINS`                   | backend           | `http://localhost:5173,http://localhost:3000`                   |
| `LLM_BASE_URL`                   | backend           | `http://ollama:11434/v1`                                        |
| `LLM_API_KEY`                    | backend           | `ollama` (для Ollama — любая непустая строка)                   |
| `LLM_MODEL`                      | backend, Makefile | `qwen2.5:7b-instruct`                                           |
| `VITE_API_URL`                   | frontend (сборка) | `http://localhost:8000/api/v1`                                  |
| `BACKEND_APP`                    | compose           | `src.web.main:app` — путь к ASGI-приложению для uvicorn         |
| `BIND_HOST`                      | compose           | `127.0.0.1`; `0.0.0.0` — показать демо по локальной сети        |
| `OLLAMA_IMAGE`                   | compose           | `ollama/ollama:latest`                                          |

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
| `make build`      | пересобирает образы                                                         |
| `make logs`       | показывает логи всех сервисов; один сервис: `make logs s=backend`            |
| `make ps`         | показывает состояние контейнеров и healthchecks                             |
| `make migrate`    | `alembic upgrade head` в одноразовом контейнере backend                      |
| `make seed`       | загружает синтетические данные (в контейнере backend)                        |
| `make test-back`  | `uv run pytest` в `backend/` на хосте                                       |
| `make lint-back`  | `ruff check` + `ruff format --check` в `backend/` на хосте                  |
| `make lint-front` | `npm run lint` в `frontend/` на хосте                                        |
| `make llm-up`     | поднимает ollama и скачивает модель `LLM_MODEL`                              |

Команды бэка и фронта вынесены в переменные в начале `Makefile` (`MIGRATE_CMD`, `SEED_CMD`,
`BACK_TEST_CMD`, `BACK_LINT_CMD`, `FRONT_LINT_CMD`). Переопределить команду можно без правки файла:
`make seed SEED_CMD="python -m app.seed"`.

Полный сброс вместе с данными: `docker compose --profile llm down -v`. Эта команда удаляет и БД,
и скачанные модели.

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

Бэк работает с LLM через OpenAI-совместимый API. Ollama отдаёт такой API на `/v1`.

```bash
make llm-up            # поднимет ollama (профиль llm) и сделает ollama pull $LLM_MODEL
```

В `.env`:

```
LLM_BASE_URL=http://ollama:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5:7b-instruct
```

После правки `.env` перезапустите бэк: `make up`.

Проверка с хоста:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:7b-instruct","messages":[{"role":"user","content":"Привет"}]}'
```

Ресурсы и выбор модели:

- `qwen2.5:7b-instruct` весит около 4.7 ГБ и требует около 8 ГБ RAM. На CPU ответ занимает от
  нескольких секунд до десятков секунд; для демо этого хватает, для живого чата медленно.
- На слабом ноутбуке подойдёт `qwen2.5:3b-instruct` (около 2 ГБ): поменяйте `LLM_MODEL` и
  снова выполните `make llm-up`.
- Для NVIDIA GPU раскомментируйте блок `deploy.resources` у сервиса `ollama` в
  `docker-compose.yml`. На хосте нужен nvidia-container-toolkit.
- Если Ollama уже установлена на хосте, контейнер не нужен:
  `LLM_BASE_URL=http://host.docker.internal:11434/v1`. На Linux для этого добавьте бэку
  `extra_hosts: ["host.docker.internal:host-gateway"]`.
- Облачный провайдер или vLLM подключается без изменений в коде: поменяйте `LLM_BASE_URL`,
  `LLM_API_KEY` и `LLM_MODEL`.

Модели хранятся в томе `ollama_models`, поэтому при пересоздании контейнера заново не скачиваются.

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
VITE_API_URL=https://demo.example.ru/api/v1
BIND_HOST=127.0.0.1
```

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

```bash
cd /opt/kodprozr && git pull && make up              # пересборка и перезапуск; миграции применятся при старте
docker compose exec postgres pg_dump -U kodprozr kodprozr | gzip > backup_$(date +%F_%H%M).sql.gz
```

Восстановление: `gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U kodprozr kodprozr`.

## 7. Чеклист Кирилла (10–13 ноября)

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
- [ ] CI зелёный на `main`, защита ветки `main` включена (обязательный CI, PR).
- [ ] `pre-commit install` выполнен у всей команды.

### День 2 — 11.11: стенд

- [ ] VPS, домен, DNS, Caddy с HTTPS, `.env` стенда с нормальным паролем БД.
- [ ] `make up && make seed` на стенде, проверка `https://<домен>/health` и основных экранов.
- [ ] Решить вопрос LLM: локальная Ollama на стенде или облачный endpoint. Замерить время анализа одного обращения.
- [ ] Скачать модель заранее (`make llm-up`) и закрепить версию `OLLAMA_IMAGE` вместо `latest`.
- [ ] Сделать первый `pg_dump` с сидом и сохранить его вне VPS.
- [ ] Записать команду деплоя (`git pull && make up`) в чат команды и договориться, кто деплоит.

### День 3 — 12.11: фриз и запасной план

- [ ] Code freeze вечером; после него — только фиксы демо-сценария.
- [ ] Дважды прогнать демо-сценарий на стенде: с телефона, из другой сети, в режиме инкогнито.
- [ ] Запасной вариант: ноутбук докладчика с `make up`, скачанной моделью и дампом БД. Он должен работать без интернета.
- [ ] Проверить, что после `docker compose restart` и перезагрузки VPS всё поднимается само (`restart: unless-stopped`).
- [ ] Проверить, что README и этот документ актуальны и ссылки работают.

### 13.11 — сдача

- [ ] Утром проверить `/health`, `make ps`, логи без ошибок, свободное место на диске (`df -h`).
- [ ] Ничего не деплоить после финального прогона.
