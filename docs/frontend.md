# Фронтенд

Ведут: Влад Гуселетов, Егор. Код лежит в `frontend/`, команды запуска описаны в [frontend/README.md](../frontend/README.md).
Источник правды по API и модели данных — [contracts.md](contracts.md). Если этот документ с ним расходится, прав контракт.

## 1. Стек и почему он

| Что | Версия | Зачем |
| --- | --- | --- |
| React + React DOM | 18.3.1 | команда его знает, вокруг него больше всего готовых компонентов |
| TypeScript | 5.9.3 | типы сущностей контракта ловят расхождения с бэком на этапе сборки |
| Vite | 7.3.8 (`@vitejs/plugin-react` 5.2.0) | быстрый dev-сервер, сборка в статику для nginx |
| React Router | 7.18.5 (пакет `react-router`) | маршруты страниц, фильтры в query-параметрах URL |
| TanStack Query | 5.107.1 (+ devtools) | кеш запросов, состояния загрузки и ошибки, инвалидация после мутаций |
| Mantine | 8.3.18 (`core`, `hooks`, `notifications`) | готовые таблицы, карточки, формы, бейджи, AppShell, тёмная тема из коробки: экраны собираются быстро и без своей дизайн-системы |
| @tabler/icons-react | 3.51.0 | иконки, которые Mantine использует в примерах |
| Cytoscape.js | 3.34.4 | граф связей: раскладки, стили по типу узла, подсветка цепочки. Обёртка своя (`features/relation-graph/RelationGraph.tsx`), `react-cytoscapejs` не нужен: он давно не обновлялся, а нам хватает 90 строк |
| ESLint | 9.39.5 (flat config, `typescript-eslint` 8.72.2, `react-hooks`, `react-refresh`) | единые правила, ловит ошибки хуков |
| Prettier | 3.9.10 | форматирование, конфликтует с ESLint только через `eslint-config-prettier` |

Все версии зафиксированы точно (без `^`), есть `package-lock.json`. Обновлять их до сдачи не стоит.

## 2. Структура каталогов

Используем облегчённый feature-sliced. Импорты идут сверху вниз: `pages → features → shared`. Фича не импортирует страницу, `shared` не импортирует фичи. Алиас `@/` указывает на `src/`.

```
frontend/
├── Dockerfile, nginx.conf        # сборка → nginx:80, SPA-фоллбэк
├── .env.example                  # VITE_API_URL, VITE_USE_MOCKS, VITE_MOCK_DELAY_MS
└── src/
    ├── main.tsx
    ├── app/                      # всё, что про приложение целиком
    │   ├── App.tsx, providers.tsx    # MantineProvider, QueryClient, Notifications
    │   ├── router.tsx                # таблица маршрутов
    │   ├── theme.ts, global.css      # тема Mantine (синий #1D3F9E из variants.html)
    │   └── layout/AppLayout.tsx      # шапка, боковое меню, бейдж «Моки», переключатель темы
    ├── shared/                   # не знает о бизнес-сценариях
    │   ├── api/
    │   │   ├── types.ts              # типы всех сущностей и ответов контракта
    │   │   ├── client.ts             # request(): fetch или моки, ApiError
    │   │   ├── endpoints.ts          # api.<ресурс>.<метод>(): одна функция на эндпоинт
    │   │   └── mocks/                # seed.ts (данные), db.ts (сборка ответов), index.ts (роутинг)
    │   ├── config/env.ts, routes.ts  # переменные окружения; функции путей страниц
    │   ├── lib/format.ts, labels.ts  # форматирование дат и денег; русские подписи и цвета енумов
    │   └── ui/                       # PageHeader, QueryState, RiskScoreBadge, FlagBadge
    ├── features/                 # кусок сценария: хуки запросов + компоненты
    │   ├── stats/                    # useOverview, useRecomputeRisk, StatCards
    │   ├── organs/                   # useOrgans, OrganSelect
    │   ├── officials/                # useOfficials/useOfficial/useOfficialGraph, таблица, фильтры, секции профиля
    │   ├── risk-flags/               # FlagList: объяснение, legal_ref, evidence, выбор флага
    │   ├── relation-graph/           # RelationGraph (Cytoscape), graphStyle, GraphLegend
    │   ├── appeals/                  # хуки, таблица, фильтры, форма, HighlightedText, панель анализа
    │   ├── reports/                  # useReport/useCreateReport, CreateReportButton, ReportView
    │   └── assistant/                # useAskAssistant, AssistantChat
    └── pages/                    # страница = маршрут, только компоновка фич
        ├── overview/                 # /
        ├── officials/                # /officials
        ├── official-profile/         # /officials/:id
        ├── appeals/                  # /appeals
        ├── appeal-new/               # /appeals/new
        ├── appeal/                   # /appeals/:id
        ├── report/                   # /reports/:id
        ├── assistant/                # /assistant
        └── not-found/                # *
```

## 3. Экраны: что готово

Все экраны работают на моках, вёрстка рабочая, без полировки.

| Экран | Маршрут | Что есть |
| --- | --- | --- |
| Обзор | `/` | счётчики `/stats/overview` (служащие, флаги по уровням, обращения по статусам), топ-10 по риску, кнопка «Пересчитать риск» (`POST /risk/recompute`) |
| Рейтинг служащих | `/officials` | поиск по ФИО с debounce, фильтр по органу и минимальному баллу, сортировка, пагинация, бейджи флагов. Фильтры хранятся в URL. Клик по строке открывает профиль |
| Профиль служащего | `/officials/:id` | шапка с баллом, должности, полномочия со scope, родственники, компании (свои и через родственников, число и сумма контрактов). Флаги с объяснением, нормой и evidence. Граф Cytoscape: узлы разного цвета и формы по типу, цвет рамки по риску, легенда. При клике по флагу подсвечивается его цепочка evidence, остальное приглушается. Клик по узлу-служащему открывает его профиль, по узлу-обращению — карточку обращения. Кнопка «Сформировать докладную» |
| Обращения | `/appeals` | список с фильтрами по статусу и категории (в URL), бейджи категории и статуса |
| Новое обращение | `/appeals/new` | форма: текст и канал, `POST /appeals`, затем переход в карточку |
| Карточка обращения | `/appeals/:id` | текст с подсветкой сущностей по `start/end` и легендой типов, категория, уверенность, конкретность, сигналы, маршрут, резюме, ссылки на связанных служащих с баллом, кнопка «Повторный анализ» |
| Докладная | `/reports/:id` | текст черновика, кнопка «Копировать», ссылка обратно в профиль |
| Ассистент | `/assistant` | чат «вопрос — ответ», источники ответа ссылками на профили и обращения, примеры вопросов |

Заглушки и что не сделано:
- Ответ ассистента в моках собран по шаблону: это топ служащих по риску плюс найденные в вопросе ФИО. Настоящий ответ будет приходить от бэка.
- Анализ нового обращения в моках работает на регулярках: категория по ключевым словам, ФИО, суммы и даты. Настоящий разбор делает LLM на бэке.
- Моки хранят состояние в памяти вкладки. После перезагрузки страницы созданные обращения и докладные пропадают, а `/reports/:id` такой докладной вернёт 404.
- Не сделано: печать докладной, фильтр рейтинга по правилу, журнал действий аналитика (ADR-09), авторизация.

## 4. Работа с API

Цепочка вызова: компонент → хук фичи (`features/<фича>/api.ts`, TanStack Query) → `api.*` (`shared/api/endpoints.ts`) → `request()` (`shared/api/client.ts`) → `fetch` или моки.

- `request()` собирает URL из `VITE_API_URL`, выкидывает пустые query-параметры, шлёт JSON и разбирает ответ.
- При ошибке `request()` бросает `ApiError(status, message, payload)`. Текст ошибки берётся из `detail`, `error.message` или `message`. Окончательный формат ошибки описан в `docs/backend.md`, клиент поддерживает все три варианта.
- Состояния загрузки, ошибки и пустого результата отрисовывает `<QueryState query={...}>{(data) => ...}</QueryState>`. Ошибка показывается с кнопкой «Повторить».
- Ключи кеша описаны в фабрике `xxxKeys` в том же `api.ts`. После мутаций инвалидируем по префиксу: например, `useRecomputeRisk` сбрасывает `['stats']` и `['officials']`.

### Как добавить запрос

1. Тип ответа или параметров добавляем в `shared/api/types.ts`. Поле, которого нет в контракте, помечаем `/** ДОДУМАНО: ... */` и выносим на обсуждение (раздел 7).
2. Функцию эндпоинта добавляем в `shared/api/endpoints.ts`, например `get: (id) => request<Foo>('GET', `/foo/${id}`)`.
3. Хук добавляем в `features/<фича>/api.ts`: `useQuery({ queryKey: fooKeys.detail(id), queryFn: () => api.foo.get(id) })`. Для изменения данных пишем `useMutation` с инвалидацией.
4. Обработчик добавляем в `shared/api/mocks/index.ts`, одной строкой в `routes`. Если нужны данные, кладём их в `seed.ts`, а сборку ответа пишем в `db.ts`.

### Как добавить страницу

1. Создаём `src/pages/<имя>/<Имя>Page.tsx` с именованным экспортом `export function <Имя>Page()`.
2. Путь добавляем в `shared/config/routes.ts`. Ссылки строим только через `routes.xxx()`, строки путей в компонентах не пишем.
3. Маршрут регистрируем в `app/router.tsx`. Если странице нужен пункт меню, добавляем его в `NAV` в `app/layout/AppLayout.tsx`.
4. Страница только компонует фичи. Логику и запросы держим в `features/`, а компонент, нужный нескольким фичам, переносим в `shared/ui`.

## 5. Моки и переход на реальный бэк

Моки реализованы флагом, без MSW: при `VITE_USE_MOCKS=true` функция `request()` лениво импортирует `shared/api/mocks` и отдаёт ответ из памяти с задержкой `VITE_MOCK_DELAY_MS`. Модуль моков вынесен в отдельный чанк. Компоненты и хуки не знают, откуда пришли данные, поэтому для переключения на бэк код менять не нужно. Пока моки включены, в шапке горит оранжевый бейдж «Моки», а в dev-режиме каждый запрос пишется в консоль (`[mock] GET /officials ...`).

Данные (`mocks/seed.ts`) вымышлены и лежат нормализованными таблицами, как в доменной модели: органы, лица, должности, назначения, полномочия, родство, компании, роли, работа, контракты, флаги, обращения. Профиль, граф, рейтинг и статистику `mocks/db.ts` собирает из этих таблиц, поэтому они не противоречат друг другу. Ответы клонируются через `structuredClone`, чтобы компонент не мог случайно изменить «базу».

Что лежит в данных:
- **Демо-кейс H1.** Соколов Андрей Викторович, начальник отдела государственных закупок Минстроя, полномочия `procurement`. Его супруга Соколова Марина Олеговна — единственный учредитель ООО «ДорСтройРесурс», у которого 5 контрактов с тем же министерством. Флаги R01 (high), R05, R06, R07, балл 93. Имена совпадают с [data.md §4](data.md#4-заложенные-схемы).
- Ещё 14 служащих в 4 органах с баллами от 0 до 65 и разными правилами R02–R08. Двое служащих чистые.
- 8 обращений: 7 с анализом по всем пяти категориям и одно в статусе `new` без анализа. Смещения сущностей вычисляются из текста, поэтому подсветка всегда совпадает.

Переход на бэк:
1. В `frontend/.env` ставим `VITE_USE_MOCKS=false`, при необходимости правим `VITE_API_URL`, затем перезапускаем `npm run dev`.
2. Проверяем, что в `CORS_ORIGINS` бэка есть `http://localhost:5173`.
3. Проходим экраны. Если ответ не совпал с типом, сверяем его с контрактом и правим ту сторону, которая отступила от контракта (правило из [plan.md](plan.md)). Мок обновляем вслед за контрактом.
4. Моки не удаляем: на них работает демо при упавшем бэке (риск из plan.md) и проверяется вёрстка. В Docker моки включаются через `--build-arg VITE_USE_MOCKS=true`.

## 6. Соглашения

- **Именование.** Компоненты в PascalCase, файл называется по компоненту: `OfficialsTable.tsx`. Хуки начинаются с `use`, ключи кеша называются `xxxKeys`. Каталоги пишем в kebab-case (`relation-graph`, `official-profile`). Экспорты только именованные, default не используем.
- **Типы.** Поля API оставляем в snake_case, как в JSON, без маппинга в camelCase. Типы импортируем через `import type` (это проверяет ESLint).
- **Стили.** Используем props Mantine (`gap`, `c`, `fw`, `p`), компоненты `Stack`/`Group`/`SimpleGrid`. Если стилей больше нескольких свойств, заводим `Компонент.module.css` рядом с компонентом. Глобальный CSS не трогаем, цвета берём из темы (`brand`, `red`, `orange`, `gray`). Тёмная тема должна оставаться рабочей: переключатель в шапке.
- **Подписи енумов** (уровни риска, статусы, категории, типы родства, правила R01–R08) хранятся только в `shared/lib/labels.ts`, как и их цвета. Единый стиль уровней риска поддерживают `RiskScoreBadge` и `FlagBadge`.
- **Даты и деньги** выводим через `shared/lib/format.ts` (`formatDate`, `formatMoney`).
- **Переменные окружения** читаем только через `shared/config/env.ts`.
- **Перед пушем** запускаем `npm run lint` и `npm run build`. Prettier и ESLint также запускает pre-commit из корня (нужен `npm ci` в `frontend/`). CI выполняет `npm ci`, `lint` и `build`.

## 7. Пробелы контракта (→ в контракт)

Типы с пометкой `ДОДУМАНО` в `shared/api/types.ts` — это предположения фронта. Их нужно согласовать с Романом и Мишей и перенести в [contracts.md](contracts.md):

| Где | Что предположили |
| --- | --- |
| `GET /stats/overview` | `{officials_total, officials_with_flags, flags_by_severity: {high, medium, low}, appeals_total, appeals_by_status: {new, analyzed, routed, closed}, computed_at}` |
| `GET /organs` | ответ `{items, total}`, как у остальных списков |
| `GET /officials` | `position` и `organ` — строки (названия), дополнительно `organ_id`. `top_flags` — `[{rule_code, severity}]`. Значения `sort`: `-risk_score`, `risk_score`, `full_name`, `-full_name` |
| `GET /officials/{id}` | `appointments[]` расширены вложенными `position` и `organ`. `relatives[]` — `{kinship_id, kind, person}`. `companies[]` — `{company, role: founder/director/employee, share, via_person_id, via_person_name, relation: self/вид родства, started_at, ended_at, contracts_count, contracts_amount}`. `risk` — `{score, computed_at, flags[]}` |
| `GET /officials/{id}/flags` | `{items, total}` |
| `RiskFlag.evidence` | массив `[{node_id, type, label}]`, где `node_id` совпадает с `id` узла из `/graph`. На этом держится подсветка цепочки |
| `Authority.scope` | `{okpd2?: string[], okved?: string[], territory?: string}` |
| `GraphEdge.type` | `works_in`, `kinship`, `founder`, `director`, `employment`, `supplier`, `customer`, `mentions` |
| Енумы | `Company.status`: `active`/`liquidating`/`liquidated`; `Contract.method`: `auction`/`tender`/`quotation`/`single_supplier`; `Appeal.channel`: `web`/`email`/`hotline`/`letter`/`personal` |
| `Appeal.analysis` | `null`, пока обращение в статусе `new` |
| `GET /appeals/{id}` | `Appeal` плюс `linked_persons: [{id, full_name, position, organ, risk_score}]` |
| `POST /risk/recompute` | `{officials_processed, flags_total, computed_at}` |
| `assistant sources[].type` | `person`, `company`, `organ`, `contract`, `appeal`, `flag` |

## 8. Что делать в первую очередь и как поделить работу

Разделение повторяет [plan.md](plan.md). Каталоги у двух человек почти не пересекаются, поэтому конфликтов слияния мало.

**Влад Гуселетов** — `app/`, `shared/`, `features/{stats,organs,officials,risk-flags,reports,assistant}`, `pages/{overview,officials,official-profile,report,assistant}`:
1. Согласовать с бэком раздел 7, прежде всего форму `/officials`, `/officials/{id}` и `evidence`. Это нужно к КТ1 (11.11, 14:00).
2. К КТ2 перевести рейтинг и профиль на реальный API и проверить состояния загрузки и ошибок.
3. Экран докладной: печать (`window.print()` и print-стили), при необходимости редактирование текста перед копированием.
4. Полировка: пустые состояния, фильтр рейтинга по правилу, единый стиль уровней риска. Если останется время, UI ассистента на реальном `/assistant/ask`.

**Егор** — `features/{relation-graph,appeals}`, `pages/{appeals,appeal-new,appeal}`:
1. Граф: подобрать раскладку под реальный объём (сейчас `cose`), проверить подсветку `evidence` на данных бэка, добавить подсказку по узлу. К КТ2 подключить `/officials/{id}/graph`.
2. Обращения на реальном API: `POST /appeals` с ожиданием LLM (лоадер, таймаут), повторный анализ.
3. Сквозной переход «обращение → профиль → граф» для демо ([demo.md](demo.md)).
4. Скриншоты для слайдов снимать с реального стенда.

Общие файлы `shared/api/types.ts`, `endpoints.ts`, `mocks/*` и `app/router.tsx` правим маленькими PR и сразу вливаем. Если меняется тип из контракта, в том же PR обновляем `contracts.md`.
