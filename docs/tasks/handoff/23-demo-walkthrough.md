# Handoff: #23 — проход demo.md в браузере (F-07, F-09, F-10, F-16)

- Issue: #23, ответственные: Soerxq (Влад Г.), F-16 — durnoi-chel (Егор). Зона front.
- Ветка: `feat/tskfrntnd-23-demo-walkthrough` (от `origin/dev`, `origin/dev` с #27–#30 уже влит merge-коммитом).
- PR ещё не открыт.

## Что сделано

- `frontend/e2e/demo.spec.ts`, `frontend/playwright.config.ts`, `frontend/tsconfig.e2e.json`; devDependency
  `@playwright/test` 1.62.1; скрипты `npm run e2e` и `npm run e2e:video` (`DEMO_VIDEO=1`, `DEMO_SLOWMO`).
  Env: `BASE_URL`, `API_URL`, `DEMO_VIDEO`, `DEMO_SLOWMO`, `PW_CHANNEL`. Выходы e2e в `.gitignore`,
  `.prettierignore`, игнорах ESLint. В CI e2e не добавлен.
- Тест 1 проходит все шаги нового docs/demo.md на 1920×1080, падает на console.error / pageerror / 4xx/5xx.
  Баллы не зашиты: проверяется место Соколова (2–5 → 1) и рост балла, R02–R05 в первой тройке фильтра,
  N1 Орлов в нижней четверти среди служащих с флагами. Тест 2: пустые состояния, 503 с «Повторить», 404.
- Полировка фронта (F-09):
  - граф: широкий уровень раскладки переносится в несколько колонок (граф H1 стал читаемым), вписывание
    ограничено масштабом 1.4 (`graphModel.ts`, `RelationGraph.tsx`);
  - цепочки evidence в карточках флагов переносятся, без обрезки и капса (`FlagList.tsx`);
  - обрезка бейджей статуса/категории в списке обращений (`AppealsTable.tsx`);
  - дубль React-key в таблице компаний профиля (два периода работы в одной компании) — давал console.error
    (`ProfileSections.tsx`);
  - запросы не повторяются на 4xx (`providers.tsx`).
- docs/frontend.md: раздел 5.1 «E2E-прогон сценария демо», обновлён §3; строка в frontend/README.md.

## Проверки, которые реально прошли (после merge origin/dev, свежий сид)

- `npm run e2e` на стенде 5184/8104: 2 passed (сценарий 14 с, состояния 7 с). Вывод:
  Соколов 3-е место, 73 → 1-е, 88; разбор H1 `fallback: procurement`; N1 Орлов 35-е из 38 с флагами.
- `npm run e2e:video`: видео `e2e/test-results/**/video.webm` пишется (до merge).
- Финальный прогон на коммите ee7f058: `npm run lint`, `npx prettier --check .`, `tsc --noEmit` (app и e2e),
  `npm run build`, `npm test` (14/14) — зелёные.
- Старый `tests/browser.mjs` на моках (порт 5185): PASS.
- Скриншоты: `frontend/e2e/screenshots/` (не в git), ключевые скопированы в scratchpad координатора `screens/`.

## Что не сделано

- PR в `dev` с `Closes #23`, `python3 scripts/check_workflow.py --repo avt0b/kod_prozr_2026 --pr <N>`, ожидание CI.
- Проверка с LLM: Ollama на 11434 не отвечала, всё прогнано на фоллбэке.

## Следующий шаг

```bash
cd frontend
npm run lint && npx prettier --check . && npx tsc -b && npm run build && npm test
# свежий сид в контейнере (дамп после сида с кодом dev от 15.11 лежит внутри контейнера)
docker exec kodprozr-front-pg pg_restore -U kodprozr -d kodprozr --clean --if-exists /tmp/seed.dump
BASE_URL=http://localhost:5184 API_URL=http://localhost:8104/api/v1 npm run e2e
cd .. && gh pr create --base dev --head feat/tskfrntnd-23-demo-walkthrough ...   # Issue: #23, Closes #23
```

## Запущенные процессы и как остановить

- Контейнер `kodprozr-front-pg` (postgres:16.15-alpine, 127.0.0.1:55436, `--rm`): `docker stop kodprozr-front-pg`.
- Бэк uvicorn на 8104 (`LLM_BASE_URL=` пусто, `CORS_ORIGINS=http://localhost:5184,...`):
  `kill $(lsof -t -i :8104)`.
- Фронт vite dev на 5184 (`VITE_USE_MOCKS=false VITE_API_URL=http://localhost:8104/api/v1`): `kill $(lsof -t -i :5184)`.
- Мок-сервер на 5185 запускался с `timeout 120` и уже завершился.

## Известные проблемы (бэк/данные, не чинились)

- Фоллбэк относит H1 к `procurement`: 4 «закупочных» совпадения против 1 «жене»
  (`rule_based_analyzer.py`, выбор по числу совпадений). В новом demo.md это уже учтено.
- Счётчики стенда: 162 служащих, 106 обращений, 1973 контракта; в речи demo.md — «150 служащих».
- Граф H1 (depth 2) не показывает «номинального директора с 6 компаниями»: видны только директор(а)
  ДорСтройРесурс, их другие компании в граф не попадают — реплику demo.md 3:50 подтвердить или убрать.
- Ребро родства супруги в графе приходит дважды (оба направления), на экране две линии «супруг(а)».
- В тексте докладной обращения названы по UUID («Обращение 4aaed55a-…»), для бумажного документа неудобно.
- Подпись контрактного узла в `evidence` — длинный список всех контрактов; фронт теперь переносит её.
