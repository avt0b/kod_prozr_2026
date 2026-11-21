# Общий контракт проекта

Единый источник правды для бэка, фронта, ИИ и DevOps. Меняем только через обсуждение в команде:
кто меняет контракт, тот обновляет этот файл в том же PR.

## Монорепозиторий

```
kod_prozr_2026/
├── backend/          # FastAPI, Python 3.12, DDD (по образцу ~/Projects/backend/optimus)
├── frontend/         # React + TypeScript + Vite
├── docs/             # решения, план, контракты
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Порты и переменные окружения

Авторизация: [контракт login/refresh/logout/me и установка](auth.md).
Бизнес-API требует Bearer JWT; health публичный. Добавление авторизации описано
в issue #62 и требует обновления автоматизированных потребителей.

| Сервис   | Порт (хост) | Внутри compose      |
| -------- | ----------- | ------------------- |
| postgres | 5432        | `postgres:5432`     |
| backend  | 8000        | `backend:8000`      |
| frontend | 5173 (dev), 3000 (prod, nginx) | `frontend:80` |

| Переменная        | Где      | Пример                                                        |
| ----------------- | -------- | ------------------------------------------------------------- |
| `DATABASE_URL`    | backend  | `postgresql+asyncpg://kodprozr:kodprozr@postgres:5432/kodprozr` |
| `CORS_ORIGINS`    | backend  | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000` |
| `LLM_BASE_URL`    | backend  | OpenAI-совместимый endpoint (vLLM / Ollama / облако)          |
| `LLM_API_KEY`     | backend  | `sk-...`                                                      |
| `LLM_MODEL`       | backend  | `qwen2.5:7b-instruct`                                         |
| `VITE_API_URL`    | frontend | `http://localhost:8000/api/v1`                                |

Healthcheck бэка: `GET /health` → `200 {"status": "ok"}`.

## Доменная модель

Все id — UUID. JSON в snake_case. Даты — ISO 8601.

| Сущность        | Поля (основные)                                                                 |
| --------------- | -------------------------------------------------------------------------------- |
| `Person`        | id, full_name, inn?, birth_date?, address?, phone?                               |
| `Organ`         | id, name, inn, region                                                            |
| `Position`      | id, organ_id, title, department, is_corruption_risky                             |
| `Appointment`   | id, person_id, position_id, started_at, ended_at? — замещение должности          |
| `Authority`     | id, position_id, kind (`procurement`/`permits`/`inspection`/`budget`/`hr`), scope `{okpd2: string[], okved: string[], territory: string \| null}`. Пустой список кодов = любые коды |
| `Kinship`       | id, person_id, relative_id, kind (`spouse`/`child`/`parent`/`sibling`/`in_law`/`other`) |
| `Company`       | id, inn, ogrn, name, okved, address, phone, registered_at, status (`active`/`liquidating`/`liquidated`) |
| `CompanyRole`   | id, company_id, person_id, role (`founder`/`director`), share?, started_at, ended_at? |
| `Employment`    | id, person_id, company_id, started_at, ended_at? — прошлые места работы вне госслужбы |
| `Contract`      | id, reg_number, customer_organ_id, supplier_company_id, amount, signed_at, okpd2, method (`auction`/`tender`/`quotation`/`single_supplier`) |
| `RiskFlag`      | id, person_id, rule_code, rule_name, severity (`low`/`medium`/`high`), weight, explanation, evidence, legal_ref?, computed_at. `evidence` — цепочка узлов графа `[{node_id, type, label}]`, `node_id` совпадает с `id` узла из `/officials/{id}/graph`, `type` — тип узла графа |
| `RiskScore`     | person_id, score (0–100), flags_count, computed_at                              |
| `Appeal`        | id, received_at, channel (`web`/`email`/`letter`/`hotline`/`personal`), text, status (`new`/`analyzed`/`routed`/`closed`), analysis (см. ниже, `null` в статусе `new`), linked_person_ids |
| `ReportDraft`   | id, person_id, text, created_at                                                  |
| `AuditLog`      | id, actor, action (`open_profile`/`create_report`/`recompute_risk`/`submit_appeal`), object_type, object_id?, at. `object_id = null` только для общего пересчёта риска. Аутентификации нет, `actor = "analyst"` (ADR-09) |

«Служащий» = `Person`, у которого есть хотя бы одно `Appointment`.

### Анализ обращения (`Appeal.analysis`)

```json
{
  "is_corruption": true,
  "category": "bribe | conflict_of_interest | procurement | abuse_of_power | other",
  "confidence": 0.87,
  "entities": [{"type": "person|organization|position|money|date|address", "text": "...", "start": 10, "end": 25}],
  "signals": [{"code": "named_official", "text": "назван конкретный служащий"}],
  "specificity": 0.7,
  "route_to": "Подразделение по профилактике коррупционных правонарушений",
  "summary": "...",
  "engine": "llm | fallback",
  "candidates": [{"person_id": "...", "full_name": "...", "score": 0.82}]
}
```

- `engine` — чем сделан разбор: LLM или фоллбэк на правилах (ADR-05). UI показывает это честно.
- `candidates` — найденные служащие, которых не привязали автоматически (однофамильцы, упоминание
  только по должности). Привязанные лежат в `Appeal.linked_person_ids`. Эндпоинт подтверждения
  привязки — если успеваем.

## Правила риска (первая версия)

| Код | Название | Суть | Вес | Норма |
| --- | -------- | ---- | --- | ----- |
| R01 | `relative_supplier` | Служащий или родственник — учредитель/руководитель компании, которая получает контракты органа, где у служащего полномочия `procurement` | high | 273-ФЗ ст. 10, 11 |
| R02 | `own_business` | Служащий — учредитель/руководитель действующей коммерческой организации | high | 79-ФЗ ст. 17 |
| R03 | `ex_employer_supplier` | Бывший работодатель служащего (≤ 3 лет) — подрядчик его органа | medium | 273-ФЗ ст. 10 |
| R04 | `revolving_door` | После увольнения перешёл в компанию, которая была в сфере его полномочий | medium | 273-ФЗ ст. 12 |
| R05 | `shared_contacts` | У компании-подрядчика тот же адрес/телефон, что у служащего или родственника | medium | 273-ФЗ ст. 10 |
| R06 | `supplier_concentration` | Аномальная доля одного поставщика в закупках в сфере полномочий служащего | low | — |
| R07 | `appeal_mentions` | Служащий упомянут в обращениях с признаками коррупции | по числу и конкретности | — |
| R08 | `peer_anomaly` | Аномалия относительно коллег той же должности и региона (ML) | low–medium | — |

Итоговый балл: сумма весов флагов, нормированная в 0–100. Каждый флаг обязан иметь `explanation` и `evidence`.
Веса и формула нормировки — в [backend.md](backend.md#риск-движок-adr-04-методика-балла).

- **R02:** если служащий только учредитель и не руководит — `medium` с пометкой «проверить передачу
  доли в доверительное управление» (владение долей само по себе не запрещено). Руководство — `high`.
- **R03:** контракт органа заключён в период назначения и не позже 3 лет после ухода от работодателя.
- **R04:** переход (работа, учредитель или директор) не позже 2 лет после увольнения в компанию,
  получавшую контракты органа в период назначения.
- **R05:** адреса и телефоны сравниваются после нормализации; адрес или телефон, на котором больше
  5 компаний, считается адресом массовой регистрации и не флагуется.
- **R06:** контракты органа по кодам ОКПД2 из полномочия `procurement` в период назначения; при
  4+ контрактах доля одного поставщика по сумме больше 50 % даёт `low`. Пустая сфера — правило не
  применяется.
- **R07:** severity по сумме `confidence · specificity` обращений ([ai.md](ai.md)): одно
  расплывчатое обращение даёт только `low`.

## API (`/api/v1`)

Доступ по ролям (#70, [auth.md](auth.md#роли)): таблица ниже — рабочее место, открыто
аналитику и администратору; гражданину — 403. Кабинет гражданина и администрирование —
в разделе «Роли» ниже.

| Метод | Путь | Назначение |
| ----- | ---- | ---------- |
| GET  | `/audit?object_id=&limit=20&offset=0` | Журнал действий аналитика `{items, total}`, новые сверху |
| GET  | `/stats/overview` | Счётчики для главной: служащие, флаги по уровням, обращения по статусам |
| GET  | `/risk-map?organ_id=&limit=100&offset=0` | Карта рисков должностей (вариант D): должности и органы с долей служащих с флагами, баллами, частыми правилами и типовыми рисками |
| GET  | `/organs` | Список органов |
| GET  | `/officials?query=&organ_id=&min_score=&rule_code=&sort=-risk_score&limit=20&offset=0` | Рейтинг служащих: `{items: [{id, full_name, position, organ, risk_score, top_flags[]}], total}` |
| GET  | `/officials/{id}` | Профиль: person, appointments, authorities, relatives, companies, risk `{score, flags[]}` |
| GET  | `/officials/{id}/graph?depth=2` | `{nodes: [{id, type: person|company|organ|contract|appeal, label, risk?}], edges: [{source, target, type, label}]}` |
| GET  | `/officials/{id}/flags` | Флаги риска с объяснениями |
| POST | `/risk/recompute` | Пересчитать все флаги и баллы |
| GET  | `/appeals?status=&category=&limit=&offset=` | Список обращений |
| POST | `/appeals` | `{text, channel}` → создать и проанализировать, вернуть `Appeal` |
| GET  | `/appeals/{id}` | Обращение с анализом и связанными служащими |
| POST | `/appeals/{id}/reanalyze` | Повторный анализ |
| POST | `/appeals/{id}/status` | Рассмотрение: `{status: "routed" \| "closed"}`; analyzed → routed, незакрытое → closed, иначе 409 |
| POST | `/reports` | `{person_id}` → черновик докладной записки |
| GET  | `/reports/{id}` | Черновик |
| POST | `/assistant/ask` | `{question}` → `{answer, sources: [{type, id, label}]}` |

Списки возвращают `{items, total}`, `limit` не больше 100. Формат ошибок — ProblemDetails, описан в
[backend.md](backend.md#формат-ошибок).

### Формы ответов

Поля сверх перечисленных допустимы: фронт их игнорирует.

**`GET /stats/overview`**

```json
{
  "officials_total": 150, "officials_with_flags": 31,
  "flags_by_severity": {"high": 12, "medium": 20, "low": 9},
  "appeals_total": 101, "appeals_by_status": {"new": 0, "analyzed": 101, "routed": 0, "closed": 0},
  "computed_at": "2026-11-11T12:00:00Z"
}
```

`computed_at` — время последнего пересчёта риска, `null`, если пересчёта ещё не было.

**`GET /risk-map`** (AI-11, вариант D)

```json
{
  "items": [{
    "position_id": "...", "title": "Начальник отдела закупок", "department": "Отдел закупок",
    "organ_id": "...", "organ": "Департамент строительства ...", "is_corruption_risky": true,
    "authorities": ["procurement"], "risk_level": "high",
    "typical_risks": [{"code": "procurement_affiliated_supplier", "title": "Аффилированный поставщик",
                       "description": "...", "authority": "procurement",
                       "rule_codes": ["R01", "R03", "R05"], "legal_ref": "273-ФЗ ст. 10, 11; ..."}],
    "officials_total": 1, "officials_with_flags": 1, "flagged_share": 1.0,
    "avg_score": 79.0, "max_score": 79.0,
    "top_rules": [{"rule_code": "R01", "count": 1}],
    "top_officials": [{"id": "...", "full_name": "Соколов Андрей Викторович", "risk_score": 79.0}]
  }],
  "total": 57,
  "organs": [{"organ_id": "...", "organ": "...", "positions_total": 20, "officials_total": 58,
              "officials_with_flags": 11, "flagged_share": 0.19, "avg_score": 5.9, "max_score": 80.0,
              "top_rules": [...], "top_officials": [...]}],
  "computed_at": "2026-11-15T12:00:00Z"
}
```

- Служащий относится к своей **текущей** должности, как в рейтинге (`position`/`organ` в
  `GET /officials`). Должности без замещающих служащих в карту не входят.
- `items` — должности, по убыванию `avg_score`, затем `max_score`; `total` — число должностей,
  `limit` по умолчанию 100. `organs` — сводка тех же служащих по органам, без пагинации.
  `organ_id` оставляет должности и сводку одного органа.
- `flagged_share` — доля служащих с хотя бы одним флагом (0–1), `avg_score` и `max_score` —
  по баллам 0–100. `top_rules` — до 5 правил по числу служащих с флагом, `top_officials` —
  до 3 служащих с флагами по баллу.
- `risk_level` и `typical_risks` описывают **должность**, а не людей: они зависят только от
  полномочий (`Authority.kind`) и признака `is_corruption_risky`. `high` — есть `procurement`,
  `permits` или `inspection`; `medium` — есть `budget` или `hr`, либо должность в перечне
  коррупционно-опасных; иначе `low`. `typical_risks[].rule_codes` — правила, которыми система
  ищет этот риск (пусто — система его не проверяет), `authority` — вид полномочия.
  Извлечение полномочий из текста регламента (`POST /positions/analyze-regulation`) в контракт
  не входит.

**`GET /officials`** — элемент списка:

```json
{"id": "...", "full_name": "Соколов Андрей Викторович", "position": "Начальник отдела закупок",
 "organ": "Департамент строительства ...", "organ_id": "...", "risk_score": 87.0,
 "top_flags": [{"rule_code": "R01", "severity": "high"}]}
```

`position` и `organ` — названия текущей должности и органа. `top_flags` — до 3 флагов по весу.
`sort`: `-risk_score` (по умолчанию), `risk_score`, `full_name`, `-full_name`. При равном балле
выше тот, у кого больше флагов. `rule_code` (`R01`…`R08`) оставляет служащих с флагом этого правила.

**`GET /officials/{id}`**

```json
{
  "person": {"id": "...", "full_name": "...", "inn": null, "birth_date": null, "address": "...", "phone": "..."},
  "appointments": [{"id": "...", "person_id": "...", "position_id": "...", "started_at": "...", "ended_at": null,
                    "position": {Position}, "organ": {Organ}}],
  "authorities": [{Authority}],
  "relatives": [{"kinship_id": "...", "kind": "spouse", "person": {Person}}],
  "companies": [{"company": {Company}, "role": "founder | director | employee", "share": 100,
                 "via_person_id": "...", "via_person_name": "...", "relation": "self | spouse | ...",
                 "started_at": "...", "ended_at": null, "contracts_count": 5, "contracts_amount": 38000000}],
  "risk": {"score": 87.0, "computed_at": "...", "flags": [{RiskFlag}]}
}
```

`companies` — компании служащего и его родственников: роли учредителя и директора, а также места
работы служащего (`role = "employee"`). `contracts_*` — контракты компании с органами, где служащий
замещал должность. `authorities` — полномочия текущих должностей.

**`GET /officials/{id}/graph`** — `{nodes, edges}`. `node.type`: `person`, `company`, `organ`,
`contract`, `appeal`. `edge.type`: `works_in` (служащий → орган, label — должность), `kinship`,
`founder`, `director`, `employment`, `supplier` (компания → контракт), `customer` (контракт → орган),
`mentions` (обращение → служащий), `shared_contact` (человек ↔ компания с тем же адресом или
телефоном, R05). Узлы из `evidence` флагов служащего всегда входят в граф. `depth` от 1 до 3, по умолчанию 2.

**`GET /officials/{id}/flags`** — `{items: [RiskFlag], total}`, по убыванию веса.

**`POST /risk/recompute`** — `{officials_processed, flags_total, computed_at}`.

**`GET /appeals/{id}`** — `Appeal` плюс `linked_persons: [{id, full_name, position, organ, risk_score}]`.

**`POST /assistant/ask`** — `sources[].type`: `person`, `company`, `organ`, `contract`, `appeal`, `flag`.


### Свёртка контрактов и журнал (B-11, B-18)

Граф сворачивает контракты одной пары поставщик/орган в один узел с числом и полной суммой.
ID: `uuid5(NAMESPACE_URL, f"kodprozr:contracts:{company_id}:{organ_id}")`.
Риск-движок приводит контрактные `evidence[].node_id` всех правил к тому же ID, сохраняя
фактические подписи исходных контрактов. Свёртка графа учитывает все контракты пары;
флаг описывает только контракты, соответствующие условиям правила. Лимит — 150 узлов,
`truncated=true` при неполноте графа или исчерпании лимита входных контрактов.

`GET /audit` — чтение журнала с фильтром UUID `object_id`, пагинацией до 100 записей.
Профиль, докладная и упоминания обращения имеют также записи с `object_type=person`
и `object_id` служащего, чтобы журнал можно было показать в его профиле. Создание обращения
дополнительно записывается по ID самого обращения; полный пересчёт — с типом `risk` и
`object_id=null`. Записи сохраняются в транзакции операции, неуспешные операции их не оставляют.


### Ассистент B-19

Форма `POST /assistant/ask` сохраняется. Сервер вызывает один инструмент чтения из фиксированного
набора (поиск/профиль служащего, родственники среди поставщиков, верх рейтинга, обращения,
компании), максимум 20 результатов. `sources` — IDs реальных результатов БД. При недоступной LLM
типовые вопросы разбираются детерминированно; неоднозначность требует уточнения, неподдерживаемые
вопросы получают отказ с примерами. Операции записи и произвольный SQL не поддерживаются.

### Ручные аналитические схемы (#64)

`/graph-workspaces` — отдельный слой ручных объектов и связей в `manual_graph`.
Владелец изменяет схему, выбранные пользователи только читают. Права привязаны
к JWT-сессии; исходный граф, правила риска и доказательства не меняются.
Полный контракт и ограничения: [manual-graph.md](manual-graph.md).

### Роли (#70)

`role` пользователя: `citizen` | `analyst` | `admin`; приходит в `user` ответов
`/auth/login`, `/auth/refresh`, `/auth/register` и в `/auth/me`. Роль проверяется по БД
на каждом запросе, поэтому смена роли или блокировка действуют сразу.

| Метод | Путь | Роль | Назначение |
| ----- | ---- | ---- | ---------- |
| POST | `/auth/register` | — | `{username, password}` → гражданин и сессия (как login); 409, если логин занят |
| POST | `/citizen/appeals` | citizen | `{text}` (20–20 000 символов) → `{id, received_at, text, status}`; анализ как у `POST /appeals` |
| GET  | `/citizen/appeals?limit=&offset=` | citizen | Свои обращения `{items, total}`, новые сверху; без анализа и служащих |
| GET  | `/admin/users?role=&query=&limit=&offset=` | admin | `{items: [{id, username, role, active}], total}` |
| POST | `/admin/users` | admin | `{username, password, role}` → пользователь; 409, если логин занят |
| PATCH | `/admin/users/{id}` | admin | `{role?, active?, password?}`; любое изменение отзывает сессии пользователя |
| DELETE | `/admin/users/{id}` | admin | 204; 409, если у пользователя есть данные (схемы графа) — тогда блокировать |

Последнего активного администратора нельзя разжаловать, заблокировать или удалить (409).
