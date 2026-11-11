# Фронтенд «Код прозрачности»

Рабочее место аналитика подразделения по профилактике коррупции.
Стек: React 18, TypeScript, Vite, Mantine, TanStack Query, React Router, Cytoscape.js.
Подробно об устройстве, соглашениях и распределении работы написано в [docs/frontend.md](../docs/frontend.md).
API и модель данных описаны в [docs/contracts.md](../docs/contracts.md).

## Быстрый старт

Нужен Node.js 22.18+ (в CI и Docker используется 22).

```bash
cd frontend
npm ci                 # или npm install
cp .env.example .env   # по умолчанию VITE_USE_MOCKS=true, бэкенд не нужен
npm run dev            # http://localhost:5173
```

## Команды

| Команда                                   | Что делает                                              |
| ----------------------------------------- | ------------------------------------------------------- |
| `npm run dev`                             | dev-сервер Vite на :5173, режим берётся из `.env`       |
| `npm run dev:mocks`                       | dev-сервер на моках при любом `.env`                    |
| `npm run build`                           | проверка типов (`tsc -b`) и production-сборка в `dist/` |
| `npm run preview`                         | раздача собранного `dist/` на :4173                     |
| `npm run typecheck`                       | только проверка типов                                   |
| `npm run lint` / `npm run lint:fix`       | ESLint, с исправлением во втором случае                 |
| `npm run format` / `npm run format:check` | Prettier: переформатировать или только проверить        |

## Переменные окружения

Переменные читаются в `src/shared/config/env.ts`. Vite вшивает их в бандл при сборке.

| Переменная           | По умолчанию                            | Назначение                                                           |
| -------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| `VITE_API_URL`       | `http://localhost:8000/api/v1`          | базовый URL API                                                      |
| `VITE_USE_MOCKS`     | `false` (в `.env.example` стоит `true`) | `true`: запросы обслуживают in-memory моки из `src/shared/api/mocks` |
| `VITE_MOCK_DELAY_MS` | `300`                                   | искусственная задержка ответов моков                                 |

Чтобы работать с реальным бэкендом, поставьте `VITE_USE_MOCKS=false` и перезапустите `npm run dev`.
В `CORS_ORIGINS` бэкенда должен быть `http://localhost:5173`.

## Docker

Сборка multi-stage: Node собирает `dist/`, nginx раздаёт его на порту 80 с SPA-фоллбэком на `index.html` (`nginx.conf`).

```bash
docker build -t kodprozr-frontend \
  --build-arg VITE_API_URL=http://localhost:8000/api/v1 \
  --build-arg VITE_USE_MOCKS=false .
docker run --rm -p 3000:80 kodprozr-frontend   # http://localhost:3000
```

Корневой `docker-compose.yml` передаёт `VITE_API_URL` как build-arg. После смены адреса образ нужно пересобрать.
Для стенда без бэкенда можно собрать образ с `--build-arg VITE_USE_MOCKS=true`.

## Проверки задач Егора (F-11–F-16)

- `npm test` — регрессионные проверки Unicode, evidence, группировки и адаптеров API.
- `npm run test:e2e` — браузерный прогон на уже запущенном Vite (по умолчанию `http://127.0.0.1:5173`). Перед первым запуском: `npx playwright install chromium`.
- Для установленного Edge в PowerShell: `$env:TEST_BROWSER_CHANNEL='msedge'`.
- Для реального API: задайте `TEST_BASE_URL` и `TEST_API_URL`. Проверка создаёт синтетическое обращение H1 и докладную: запускать в отдельной тестовой БД.
- В браузерном прогоне проверяются фильтры, форма, ошибки сервера, разбор, R01, переход по узлу графа, R07 и граф на 150 узлах. Скриншоты сохраняются в игнорируемом `test-results/`.

Подробное воспроизведение стенда и оставшиеся зависимости — [отчёт Егора](../docs/tasks/egor-report.md).
