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

| Сервис   | Порт (хост) | Внутри compose      |
| -------- | ----------- | ------------------- |
| postgres | 5432        | `postgres:5432`     |
| backend  | 8000        | `backend:8000`      |
| frontend | 5173 (dev), 3000 (prod, nginx) | `frontend:80` |

| Переменная        | Где      | Пример                                                        |
| ----------------- | -------- | ------------------------------------------------------------- |
| `DATABASE_URL`    | backend  | `postgresql+asyncpg://kodprozr:kodprozr@postgres:5432/kodprozr` |
| `CORS_ORIGINS`    | backend  | `http://localhost:5173,http://localhost:3000`                 |
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
| `Authority`     | id, position_id, kind (`procurement`/`permits`/`inspection`/`budget`/`hr`), scope (коды ОКПД2/ОКВЭД, территория) |
| `Kinship`       | id, person_id, relative_id, kind (`spouse`/`child`/`parent`/`sibling`/`in_law`/`other`) |
| `Company`       | id, inn, ogrn, name, okved, address, phone, registered_at, status                |
| `CompanyRole`   | id, company_id, person_id, role (`founder`/`director`), share?, started_at, ended_at? |
| `Employment`    | id, person_id, company_id, started_at, ended_at? — прошлые места работы вне госслужбы |
| `Contract`      | id, reg_number, customer_organ_id, supplier_company_id, amount, signed_at, okpd2, method |
| `RiskFlag`      | id, person_id, rule_code, severity (`low`/`medium`/`high`), weight, explanation, evidence (цепочка узлов графа), legal_ref |
| `RiskScore`     | person_id, score (0–100), flags_count, computed_at                              |
| `Appeal`        | id, received_at, channel, text, status (`new`/`analyzed`/`routed`/`closed`), analysis (см. ниже), linked_person_ids |
| `ReportDraft`   | id, person_id, text, created_at                                                  |

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
  "route_to": "отдел по профилактике коррупционных правонарушений",
  "summary": "..."
}
```

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

## API (`/api/v1`)

| Метод | Путь | Назначение |
| ----- | ---- | ---------- |
| GET  | `/stats/overview` | Счётчики для главной: служащие, флаги по уровням, обращения по статусам |
| GET  | `/organs` | Список органов |
| GET  | `/officials?query=&organ_id=&min_score=&sort=-risk_score&limit=20&offset=0` | Рейтинг служащих: `{items: [{id, full_name, position, organ, risk_score, top_flags[]}], total}` |
| GET  | `/officials/{id}` | Профиль: person, appointments, authorities, relatives, companies, risk `{score, flags[]}` |
| GET  | `/officials/{id}/graph?depth=2` | `{nodes: [{id, type: person|company|organ|contract|appeal, label, risk?}], edges: [{source, target, type, label}]}` |
| GET  | `/officials/{id}/flags` | Флаги риска с объяснениями |
| POST | `/risk/recompute` | Пересчитать все флаги и баллы |
| GET  | `/appeals?status=&category=&limit=&offset=` | Список обращений |
| POST | `/appeals` | `{text, channel}` → создать и проанализировать, вернуть `Appeal` |
| GET  | `/appeals/{id}` | Обращение с анализом и связанными служащими |
| POST | `/appeals/{id}/reanalyze` | Повторный анализ |
| POST | `/reports` | `{person_id}` → черновик докладной записки |
| GET  | `/reports/{id}` | Черновик |
| POST | `/assistant/ask` | `{question}` → `{answer, sources: [{type, id, label}]}` |

Списки возвращают `{items, total}`. Формат ошибок описан в `docs/backend.md`.
