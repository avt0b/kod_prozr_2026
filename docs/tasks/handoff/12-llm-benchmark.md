# Handoff: AI-03 — выбор и проверка LLM (#12)

- **ID плана:** AI-03 (docs/tasks/vlad-o.md), issue #12, ответственный `ostrix05`, зона ai.
- **Ветка:** `feat/tskai-12-llm-benchmark` (от `origin/dev` = 038c29c, включает #28 и #30).
- **Статус:** WIP. Ollama поднята на GPU, модель скачана. Замеров, eval и правок docs/ai.md §8 ещё нет.

## Что сделано (проверено)

1. Ollama **0.12.6** (та же версия, что `OLLAMA_IMAGE=ollama/ollama:0.12.6` в .env.example),
   официальный `ollama-linux-amd64.tgz` из GitHub Releases, sha256 сверен с `sha256sum.txt` релиза
   (`de82adce…ec0a1`). Распакована без sudo в `~/.local/share/ollama-bin` (3.2 ГБ).
2. Сервер запущен на хосте: `OLLAMA_HOST=127.0.0.1:11434 setsid nohup ~/.local/share/ollama-bin/bin/ollama serve`
   (лог — `ollama-serve.log` в scratchpad сессии координатора). `curl localhost:11434/api/version` → `{"version":"0.12.6"}`.
3. **GPU работает:** в логе `inference compute library=CUDA name=CUDA0 description="NVIDIA GeForce RTX 4060 Laptop GPU"
   libdirs=ollama,cuda_v13 total="8.0 GiB" available="7.7 GiB"`. Ollama включила `low vram mode` (порог 20 ГБ),
   `OLLAMA_CONTEXT_LENGTH=4096`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=5m`.
4. Модель `qwen2.5:7b-instruct` скачана (`ollama list`: id `845dbda0ea48`, 4.7 ГБ), лежит в `~/.ollama/models`.
5. Свой Postgres `kodprozr-llm-pg` (127.0.0.1:55438) поднят на актуальном dev: миграции до 0003, сиды
   загружены (`risk: 162 officials, 57 flags`).
6. `scripts/bench_llm.py` — замер одного обращения с тем же промптом и few-shot, что у
   `LLMAppealAnalyzer` (`json_object`, `temperature=0`): прогрев отдельно, затем N обращений средней длины,
   mean/median/p95, токены, доля валидного JSON по `LLMAnswer`. **Ещё не запускался.**

## Что не сделано

- Замеры времени (mean/p95 по 10), VRAM при загруженной модели.
- Проверка бэка вживую (`engine=llm` в ответе `POST /appeals`).
- `eval --llm --limit 30`, отчёт `eval/report.llm.json`.
- Цифры в docs/ai.md §8 (решение по модели для Кирилла), PR в dev с `Refs #12`.
- При необходимости — сравнение с `qwen2.5:14b-instruct` (9 ГБ, в 8 ГБ VRAM целиком не влезет) или `qwen3:8b`.

## Следующий шаг (команды)

```bash
cd backend
export LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama LLM_MODEL=qwen2.5:7b-instruct LLM_TIMEOUT_SECONDS=90
export DATABASE_URL=postgresql+asyncpg://kodprozr:kodprozr@localhost:55438/kodprozr

# 1. Замер одного обращения (10 шт. около медианы длины) + VRAM
PYTHONPATH=. uv run python ../scripts/bench_llm.py --n 10 --out /tmp/bench.qwen2.5-7b.json
nvidia-smi --query-gpu=memory.used,memory.total --format=csv; ~/.local/share/ollama-bin/bin/ollama ps

# 2. Бэк ходит в LLM: ожидаем analysis.engine == "llm" и analyzer "llm:qwen2.5:7b-instruct"
uv run uvicorn src.web.main:app --port 18012 &
curl -s -XPOST localhost:18012/api/appeals -H 'content-type: application/json' \
  -d '{"text":"Начальник отдела закупок Соколов А. В. отдаёт контракты фирме брата."}' | jq .analysis.engine
# (префикс API проверить в src/web/main.py; после проверки — остановить uvicorn и пересидить БД)

# 3. Метрики LLM против фоллбэка на 30 обращениях — в ОТДЕЛЬНЫЙ файл, eval/report.json не трогать
uv run python -m src.eval --dir ../data/generated --out ../eval/report.llm.json --llm --limit 30
```

Затем записать фактические цифры в docs/ai.md §8 (что не измерено — так и написать), PR в dev
(`Issue: #12`, `Refs #12`, ответственный `ostrix05`). `data/generated/appeals.json` не менять:
предрасчёт AI-06 с LLM — отдельной задачей после этого PR (`make precompute` / `python -m src.seed.precompute`).

## Запущенные процессы, контейнеры, порты

| Что | Где | Как остановить |
| --- | --- | --- |
| `ollama serve` 0.12.6, GPU | 127.0.0.1:11434, бинарь `~/.local/share/ollama-bin/bin/ollama`, модели `~/.ollama/models` | `pkill -f "ollama-bin/bin/ollama serve"` (НЕ останавливать до финального прогона и AI-06) |
| Postgres `kodprozr-llm-pg` (`--rm`) | 127.0.0.1:55438 | `docker stop kodprozr-llm-pg` |

Проверка состояния: `curl -s localhost:11434/api/version`, `curl -s localhost:11434/api/tags`,
`~/.local/share/ollama-bin/bin/ollama ps` (загружена ли модель и на GPU ли она).
Перезапуск после ребута: команда из п. 2 раздела «Что сделано».

## Известные проблемы

- nvidia-container-toolkit на машине нет, поэтому Ollama из compose (`make llm-up`) работала бы на CPU;
  GPU даёт только хостовая установка. Бэк в Docker достучится до неё через `host.docker.internal` (devops.md §5).
- 8 ГБ VRAM: 7B Q4 помещается, 14B Q4 (~9 ГБ) — только с частичной выгрузкой на CPU.
- Ollama слушает только 127.0.0.1; для контейнера бэка нужен `OLLAMA_HOST=0.0.0.0:11434` или host-сеть.
