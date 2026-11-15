# Handoff: #25 — OPS-02, OPS-05, OPS-07, OPS-08

Ответственный: Shvarts999 (Кирилл). Ветка: `feat/tskdvps-25-offline-dump-video`, создана от `origin/dev`;
`origin/dev` уже слит в неё после #27–#30. PR ещё не открыт.

## Сделано (в WIP-коммитах)

- **OPS-02, сборка.** Причина сбоя 14.11 найдена: на машине bridge-сеть Docker не выходит в интернет.
  Виноват TUN `throne-tun`: DNS отвечает, а TCP висит. Отсюда `npm ci` с «Exit handler never called»
  и зависший `pip install uv`. Решение: `build.network: ${BUILD_NETWORK:-default}` в compose, а
  `make build` идёт через `docker compose build --print | docker buildx bake --allow=network.host -f -`.
  Compose 5.6 собирает через bake, и без `--allow` bake отказывает в network.host.
  **Проверено:** `make build && make reset && make smoke` занимает 54 с, результат `smoke: OK, 45 проверок`,
  балл H1 73.0 → 88.0 (после слияния B-17; до слияния было 79 → 92).
- Хост-порты параметризованы: `POSTGRES_PORT/BACKEND_PORT/FRONTEND_PORT/OLLAMA_PORT`, по умолчанию из
  contracts.md. Makefile берёт из них `API_URL`, `FRONT_URL` и `HOST_DB`.
- Баг `make reset`: `down -v` с `--profile llm` удалял том `ollama_models` вместе с моделью (проверено
  через `--dry-run`). Теперь reset вызывает `down -v` без профиля, и ollama с моделями остаются на месте
  (проверено на тестовом compose-проекте).
- **OPS-05.** У backend добавлен `extra_hosts: host.docker.internal:host-gateway`. GPU вынесен в
  `docker-compose.gpu.yml`, `make llm-up` сам определяет runtime nvidia (`LLM_GPU=auto|1|0`). Здесь
  runtime nvidia нет, поэтому CPU. Для раздачи LLM команде добавлены `OLLAMA_BIND_HOST` и `make llm-check`.
  `make llm-up` проверен только статически (`docker compose --profile llm config`): по указанию
  координатора его не запускали.
- Тег Ollama: последняя стабильная на 15.11 — `0.40.16` (manifest есть, amd64 3.4 ГБ, образ скачан
  локально). Оставлен `0.12.6`: на этой версии работает Ollama AI-03 (`/api/version` → 0.12.6), а
  смену без прогона модели проверить нельзя. Пояснение — в комментарии в `.env.example`.
- **OPS-07.** Добавлены `scripts/offline.sh bundle|load`, цели `make offline-bundle` и `make offline-load`,
  флаг `OFFLINE=1` (`--no-build --pull never`) у `up/reset/restore/llm-up`. **Не проверено** на деле.
- **OPS-08.** Добавлены цели `make dump`, `make restore FILE=...` и `make video`. `make video` выдаёт
  понятную ошибку, если нет `frontend/e2e/demo.spec.ts` или Playwright. Тест «dump → чистый стек →
  restore → smoke» был запущен в момент остановки, результат не зафиксирован.
- `.env.example`: порты, `OLLAMA_BIND_HOST`, `BUILD_NETWORK`, `LLM_GPU`, вариант «Ollama на хосте».
- `docs/devops.md`: обновлены §1–3 (порты, переменные, команды, сборка в сети хоста, reset).

## Не сделано: следующие шаги

1. Проверить dump/restore заново:
   `make reset && make dump && docker compose down -v && make up OFFLINE=1`, затем
   `make restore FILE=<последний dist/db/*.sql.gz> && make smoke`.
2. Проверить офлайн-пакет: `make offline-bundle`, затем `docker rmi kodprozr-backend:local kodprozr-frontend:local`
   (эти образы собирал этот агент), `make offline-load`, `make reset OFFLINE=1`, `make smoke`. Образ
   `ollama/ollama:0.12.6` качался в фоне; если он скачан, то попадёт в пакет (`WITH_OLLAMA=auto`).
3. `docs/devops.md`: переписать §5 (GPU/CPU; «Ollama на хосте»; общая LLM команды через SSH-туннель
   или `OLLAMA_BIND_HOST=0.0.0.0`; проблема с таймаутом, см. ниже). §6 «Обновление и бэкап» перевести
   на `make dump/restore`. Добавить §9 «Резервный ноутбук без сети, дамп, видео». В `scripts/offline.sh`
   заменить ссылку «§7» на «§9».
4. `docs/demo.md`: в строках про офлайн заменить «`make reset` с выключенной сетью» на `make reset OFFLINE=1`.
   Оговорить, что «сразу уходит на фоллбэк» неверно, если файрвол отбрасывает пакеты (DROP).
5. `.gitignore`: `dist/` уже покрыт строкой из Node-секции, можно добавить явный `/dist/`.
6. Переписать WIP-коммиты в нормальные сообщения. Прогнать `docker compose config -q` и
   `python3 scripts/check_workflow.py`. Открыть PR в `dev` с `Closes #25` и `Issue: #25`, дождаться CI.
7. В конце выполнить `make reset` и оставить стек поднятым для координатора.

## Известные проблемы

- **Таймаут LLM при DROP-файрволе.** С `LLM_BASE_URL=http://host.docker.internal:11434/v1` бэк
  получает `ConnectTimeout`: файрвол хоста отбрасывает трафик из docker-сетей и не отвечает RST.
  Бэк ждёт `LLM_TIMEOUT_SECONDS=90` и повторяет попытку, всего 180 с, поэтому в smoke `POST /appeals`
  и `/assistant/ask` упали по таймауту. Нужен отдельный короткий connect-timeout в бэке (зона B).
  Пока в локальном `.env` `LLM_BASE_URL=` (фоллбэк).
- Ollama AI-03 слушает только `127.0.0.1:11434`, и моделей в ней на момент проверки не было
  (`/api/tags` → `[]`). Вариант «бэк в Docker → Ollama на хосте» здесь заработает только с
  `OLLAMA_HOST=0.0.0.0` и правилом файрвола для 172.16.0.0/12.
- На этой машине порты 5432 и 8000 заняты чужим проектом (`postgres_kyop`, `optimus_kyop`; их не трогать).
  Локальный `.env` ворктри (не в git): `POSTGRES_PORT=15432`, `BACKEND_PORT=18000`,
  `VITE_API_URL=http://localhost:18000/api/v1`, `LLM_BASE_URL=` пусто. `make smoke` берёт порт из `.env`.
- Сиды пишут `appeals_analyzed: 0`, то есть предрасчёт анализа обращений из `data/generated` не
  загружается. Это зона AI/данных, не проверял.
- `docker-compose.gpu.yml` подключается через `-f`, и тогда `docker-compose.override.yml` не подхватывается.

## Что запущено (оставлено как есть)

- Compose-стек `kodprozr`: `kodprozr_postgres` (127.0.0.1:15432), `kodprozr_backend` (127.0.0.1:18000),
  `kodprozr_frontend` (127.0.0.1:3000). Его состояние зависит от того, где остановился тест dump/restore.
  Привести в порядок — `make reset` в этом ворктри, остановить — `make down`.
- Фоновый `docker pull ollama/ollama:0.12.6`. Образ `ollama/ollama:0.40.16` (8.5 ГБ) скачан этим агентом,
  его можно удалить: `docker rmi ollama/ollama:0.40.16`.
- Профиль `llm` не поднимался.
