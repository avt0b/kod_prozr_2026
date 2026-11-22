# Handoff: AI-11 — карта рисков должностей, вариант D

- **ID плана:** AI-11, **issue:** #22 (assignee `ostrix05`, метки `ai`, `back`, `front`)
- **Ветка:** `feat/tskai-22-position-risk-map` (от `origin/dev`, `origin/dev` после #27–#30 уже влит)
- **PR:** #32 → `dev` (`Closes #22`), `scripts/check_workflow.py --repo avt0b/kod_prozr_2026 --pr 32` — passed

## Что сделано

- Бэк, модуль `stats`: `GET /api/v1/risk-map?organ_id=&limit=100&offset=0`.
  - Должности и органы: число служащих, сколько из них с флагами и их доля, средний и максимальный балл, частые правила, топ служащих.
  - Риск должности (`risk_level`) и типовые риски (`typical_risks`) зависят только от полномочий: каталог и политика лежат в `stats/domain/position_risk.py`.
  - Порты `application/interfaces/risk_map_sources.py`, ACL `infrastructure/adapters/risk_map_acl.py`, сборка в `web/wiring.py` и `web/dependencies.py`.
  - `stats.domain` добавлен в контракты import-linter.
- Контракт описан в `docs/contracts.md` (таблица API и раздел «`GET /risk-map`»).
- Тесты бэка: `tests/unit/stats/test_risk_map.py` (6 штук), `tests/e2e/stats/test_risk_map.py` (3 штуки). В `scripts/smoke.py` добавлен блок `/risk-map` перед демо-обращением.
- Фронт: страница `/risk-map` и пункт меню «Карта рисков».
  - Карточки органов, тепловая карта «полномочие × орган», таблица должностей, панель должности со ссылками в профиль и рейтинг (`organ_id`, `rule_code`).
  - Код: `features/risk-map/*`, `pages/risk-map/RiskMapPage.tsx`; типы — в конце `types.ts`; мок — `mocks/riskMap.ts`; тест — `tests/risk-map.test.ts`.

## Проверки, которые реально прошли (после merge origin/dev)

- Бэк: `ruff check`, `ruff format --check`, `mypy src tests` (365 файлов), `lint-imports` (6 kept), `pytest` — 165 passed (e2e на `TEST_DATABASE_URL=...@localhost:55435/kodprozr_test`).
- Фронт: `npm run lint`, `prettier --check .`, `tsc --noEmit`, `npm run build`, `npm test` — 17 pass.
- `python3 scripts/smoke.py --api http://localhost:8103` — OK, 50 проверок (с демо-обращением, H1 73 → 88).
- Playwright 1920×1080 (реальный API, моки, светлая и тёмная тема): экран, клик по ячейке, панель, переходы в профиль и рейтинг работают, консоль чистая.

## Что не сделано

- CI на PR #32 на момент остановки: `data`, `detect` и `policy` — pass, `backend` и `frontend` — pending. Нужно дождаться результата.
- Извлечение полномочий из текста регламента (`POST /positions/analyze-regulation`) не делалось: оно не принято в контракт.
- Карточку `docs/tasks/vlad-o.md` (статус AI-11) обновляет координатор.

## Следующий шаг

```bash
gh pr checks 32 --repo avt0b/kod_prozr_2026 --watch   # дождаться зелёного CI, красное — чинить
git fetch origin && git merge origin/dev              # если dev ушёл вперёд, затем перепрогнать проверки
```

После зелёного CI нужно ревью: Роман (API), Егор (экран). Merge делает не агент.

## Запущенные процессы и контейнеры (оставлены работать)

| Что | Где | Остановить |
| --- | --- | --- |
| Postgres | контейнер `kodprozr-ai11-pg`, `127.0.0.1:55435` (БД `kodprozr` с полным сидом + демо-обращение, `kodprozr_test`) | `docker stop kodprozr-ai11-pg` (запущен с `--rm`) |
| Бэк | uvicorn на `:8103`, PID 1156497 | `kill 1156497` |
| Фронт dev | vite на `:5183` (реальный API 8103), PID 1156522 | `kill 1156522` |

Логи и скрипты скриншотов лежат в scratchpad сессии (`ai11-back.log`, `ai11-front.log`, `ai11-shot.mjs`, `ai11-mocks.mjs`, `risk-map*.png`). Каталог может быть очищен.

## Известные проблемы

- Фильтр рейтинга `organ_id` учитывает любое назначение в органе, а карта — только текущую должность. Поэтому при переходе «Рейтинг служащих органа» в рейтинге может оказаться чуть больше людей, чем в карточке органа.
- Должности без служащих в карту не попадают: источник — назначения. В `data/generated` все 57 должностей заняты.
- В БД стенда после smoke лежит демо-обращение. Для чистых данных: `DROP/CREATE DATABASE kodprozr`, затем `alembic upgrade head` и `python -m src.seed --dir ../data/generated`.
