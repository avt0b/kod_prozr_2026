#!/usr/bin/env bash
# Пересъёмка слайдов одной командой: свежая БД → скриншоты со стенда → сборка pptx.
#
# Стенд docker compose (make reset сносит тома, поднимает стек, миграции и сиды; фронт :3000):
#   docs/presentation/reshoot.sh
#
# Свой Postgres, бэкенд и фронт (БД из DATABASE_URL пересоздаётся, затем alembic и сиды через uv):
#   DATABASE_URL=postgresql+asyncpg://kodprozr:kodprozr@localhost:55437/kodprozr \
#   BASE_URL=http://127.0.0.1:5185 docs/presentation/reshoot.sh
#
# Режим LLM определяет запущенный бэкенд (для compose — .env). Сиды в режиме DATABASE_URL берут
# LLM_* из окружения и backend/.env; без LLM: LLM_BASE_URL= docs/presentation/reshoot.sh.
# Остальные переменные screenshots.mjs (OUT_DIR, BROWSER_CHANNEL, таймауты) передаются как есть.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pres="$root/docs/presentation"
cd "$root"

if [[ ! -d "$pres/node_modules/playwright" || ! -d "$pres/node_modules/pptxgenjs" ]]; then
  npm ci --prefix "$pres" --no-audit --no-fund
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  : "${BASE_URL:?С DATABASE_URL нужен BASE_URL фронта, который смотрит в API на этой БД}"
  echo "== Пересоздаю БД из DATABASE_URL"
  (
    cd backend
    uv run python - <<'PY'
import asyncio
import os
from urllib.parse import urlsplit

import asyncpg

parts = urlsplit(os.environ["DATABASE_URL"].replace("+asyncpg", "", 1))
db = parts.path.lstrip("/")
if parts.hostname not in {"localhost", "127.0.0.1", "::1"} or not db:
    raise SystemExit(f"Отказ: пересоздаю только локальную БД, а не {parts.hostname}/{db}")


async def main() -> None:
    conn = await asyncpg.connect(parts._replace(path="/postgres").geturl())
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{db}"')
    finally:
        await conn.close()
    print(f"БД {db} пересоздана на {parts.hostname}:{parts.port}")


asyncio.run(main())
PY
    uv run alembic upgrade head
    uv run python -m src.seed --dir ../data/generated
  )
else
  export BASE_URL="${BASE_URL:-http://localhost:3000}"
  echo "== make reset (стенд docker compose)"
  make reset
fi

echo "== Скриншоты: $BASE_URL"
node "$pres/screenshots.mjs"
echo "== Сборка pptx"
node "$pres/build.mjs"
