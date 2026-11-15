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
| `LLM_TIMEOUT_SECONDS`            | backend           | `90` — ожидание ответа (генерации) LLM                          |
| `LLM_CONNECT_TIMEOUT_SECONDS`    | backend           | `5` — ожидание соединения; затем сразу фоллбэк, без повтора     |
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
| `make seed`       | загружает `data/generated` с предрасчётом обращений и пересчитывает риск      |
| `make reset`      | сносит тома, поднимает стек с миграциями и сидами — состояние «как перед демо» |
| `make smoke`      | smoke всех эндпоинтов + демо-обращение (меняет данные: затем `make reset`)    |
| `make data`       | пересоздаёт синтетику генератором (`seed 42`), затем нужен `make precompute`  |
| `make data-check` | проверки данных data.md §7 (полный набор и `sample/`)                         |
| `make precompute` | предрасчёт анализа обращений в сиды (AI-06), демо-обращение остаётся `new`    |
| `make eval`       | метрики качества по БД после сидов, `eval/report.json`                        |
| `make test-data`  | тесты генератора                                                             |
| `make test-back`  | `uv run pytest` в `backend/` на хосте                                       |
| `make lint-back`  | `ruff check` + `ruff format --check` в `backend/` на хосте                  |
| `make lint-front` | `npm run lint` в `frontend/` на хосте                                        |
| `make llm-up`     | поднимает ollama и скачивает модель `LLM_MODEL`                              |

Команды бэка и фронта вынесены в переменные в начале `Makefile` (`MIGRATE_CMD`, `SEED_CMD`,
`BACK_TEST_CMD`, `BACK_LINT_CMD`, `FRONT_LINT_CMD`). Переопределить команду можно без правки файла:
`make seed SEED_CMD="python -m src.seed --dir data/example"`.

`precompute` и `eval` выполняются на хосте через `uv` и ходят в Postgres из compose на
`localhost:5432` (`HOST_DB`). `data/generated` монтируется в бэкенд только на чтение.

Порядок перед демо: `make reset` → `make smoke` → `make reset` (smoke отправляет демо-обращение
и поднимает Соколова на 1-е место, а на показе это делается вживую).

Версии образов закреплены в `.env.example` (`POSTGRES_IMAGE`, `OLLAMA_IMAGE`) и в Dockerfile'ах
(`python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine`).

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
  `docker-compose.yml`. На хосте нужен nvidia-container-toolkit (`docker info` должен
  показывать runtime `nvidia`); без него Ollama молча работает на CPU.
- `LLM_TIMEOUT_SECONDS=90`: 7B на CPU отвечает десятки секунд, фронт ждёт до 150 с. При
  недоступной LLM бэк уходит на фоллбэк через `LLM_CONNECT_TIMEOUT_SECONDS` (5 с), даже если
  файрвол молча отбрасывает пакеты; демо не встаёт.
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

Штатное обновление прода — релизный тег (раздел 7): образы из GHCR, бэкап перед миграциями,
health/smoke и откат. Ручной вариант ниже подходит для резервного ноутбука или для стенда,
где конвейер ещё не настроен.

```bash
cd /opt/kodprozr && git pull && make up              # пересборка и перезапуск; миграции применятся при старте
docker compose exec postgres pg_dump -U kodprozr kodprozr | gzip > backup_$(date +%F_%H%M).sql.gz
```

Восстановление: `gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U kodprozr kodprozr`.

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
5. Проверяет `GET /health` и запускает `python3 scripts/smoke.py --api http://127.0.0.1:8000 --keep-demo`.

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
- [ ] Запасной вариант: ноутбук докладчика с `make up`, скачанной моделью и дампом БД. Он должен работать без интернета.
- [ ] Проверить, что после `docker compose restart` и перезагрузки VPS всё поднимается само (`restart: unless-stopped`).
- [ ] Проверить, что README и этот документ актуальны и ссылки работают.

### 13.11 — сдача

- [ ] Утром проверить `/health`, `make ps`, логи без ошибок, свободное место на диске (`df -h`).
- [ ] Ничего не деплоить после финального прогона.
