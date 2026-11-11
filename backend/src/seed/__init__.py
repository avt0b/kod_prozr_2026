"""Загрузка синтетических данных: `python -m src.seed [--dir PATH]`.

Composition root, как src/web: знает все модули. Формат — один JSON-массив на сущность
контракта (docs/contracts.md, docs/data.md): organs.json, positions.json, authorities.json,
persons.json, appointments.json, kinships.json, employments.json, companies.json,
company_roles.json, contracts.json, appeals.json. Отсутствующий файл пропускается.
Загрузка идемпотентна (upsert по id), поэтому сид можно запускать повторно.
"""
