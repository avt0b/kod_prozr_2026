"""Проверка сгенерированных данных (`make data-check`, docs/data.md §7).

    python -m data.generator.check [data/generated]
    python -m data.generator.check data/generated/sample --partial

Ошибки (код возврата 1): поля и enum контракта, ссылочная целостность, контрольные суммы
ИНН/ОГРН, согласованность дат, наличие демо-кейсов и всех объектов из `_truth/`.
Предупреждения: отклонения объёмов и распределений от data.md §3.
"""

import json
import sys
import uuid
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from data.generator.ids import is_valid_inn, is_valid_ogrn

ENUMS = {
    ("authorities", "kind"): {"procurement", "permits", "inspection", "budget", "hr"},
    ("kinships", "kind"): {"spouse", "child", "parent", "sibling", "in_law", "other"},
    ("companies", "status"): {"active", "liquidating", "liquidated"},
    ("company_roles", "role"): {"founder", "director"},
    ("contracts", "method"): {"auction", "tender", "quotation", "single_supplier"},
    ("appeals", "channel"): {"web", "email", "letter", "hotline", "personal"},
    ("appeals", "status"): {"new", "analyzed", "routed", "closed"},
}
FIELDS = {
    "organs": ("id", "name", "inn", "region"),
    "positions": ("id", "organ_id", "title", "department", "is_corruption_risky"),
    "authorities": ("id", "position_id", "kind", "scope"),
    "persons": ("id", "full_name", "inn", "birth_date", "address", "phone"),
    "appointments": ("id", "person_id", "position_id", "started_at", "ended_at"),
    "kinships": ("id", "person_id", "relative_id", "kind"),
    "companies": ("id", "inn", "ogrn", "name", "okved", "address", "phone", "registered_at",
                  "status"),
    "company_roles": ("id", "company_id", "person_id", "role", "share", "started_at", "ended_at"),
    "employments": ("id", "person_id", "company_id", "started_at", "ended_at"),
    "contracts": ("id", "reg_number", "customer_organ_id", "supplier_company_id", "amount",
                  "signed_at", "okpd2", "method"),
    "appeals": ("id", "received_at", "channel", "text", "status", "analysis",
                "linked_person_ids"),
}  # fmt: skip
REFERENCES = {
    "positions": {"organ_id": "organs"},
    "authorities": {"position_id": "positions"},
    "appointments": {"person_id": "persons", "position_id": "positions"},
    "kinships": {"person_id": "persons", "relative_id": "persons"},
    "employments": {"person_id": "persons", "company_id": "companies"},
    "company_roles": {"person_id": "persons", "company_id": "companies"},
    "contracts": {"customer_organ_id": "organs", "supplier_company_id": "companies"},
}
# Объёмы data.md §3: (минимум, максимум) — выход за них только предупреждение.
VOLUMES = {
    "organs": (3, 3), "positions": (45, 75), "contracts": (1700, 2300), "appeals": (95, 115),
    "companies": (250, 400), "kinships": (330, 470), "employments": (220, 380),
}  # fmt: skip
DEMO = {
    "H1": "Соколов Андрей Викторович",
    "C2": "Лебедева Ольга Николаевна",
    "C3": "Гусев Павел Сергеевич",
    "C4": "Морозов Денис Игоревич",
    "C5": "Белова Ирина Андреевна",
    "C6": "Карпов Евгений Юрьевич",
    "N1": "Орлов Сергей Михайлович",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load(directory: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    rows = {name: json.loads((directory / f"{name}.json").read_text("utf-8")) for name in FIELDS}
    truth_dir = directory / "_truth"
    truth = {
        name: json.loads((truth_dir / f"{name}.json").read_text("utf-8"))
        for name in ("schemes", "appeals_labels", "peer_anomalies")
        if (truth_dir / f"{name}.json").is_file()
    }
    return rows, truth


def _is_date(value: Any) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def check_schema(rows: dict[str, list[dict[str, Any]]], r: Report) -> None:
    for name, fields in FIELDS.items():
        seen: set[str] = set()
        for index, row in enumerate(rows[name], start=1):
            where = f"{name}.json: запись {index}"
            missing = [f for f in fields if f not in row]
            if missing:
                r.error(f"{where}: нет полей {missing}")
                continue
            try:
                uuid.UUID(row["id"])
            except ValueError:
                r.error(f"{where}: id не UUID")
            if row["id"] in seen:
                r.error(f"{where}: повтор id {row['id']}")
            seen.add(row["id"])
            for (entity, field), allowed in ENUMS.items():
                if entity == name and row[field] not in allowed:
                    r.error(f"{where}: {field}={row[field]!r} вне enum контракта")
            for field in ("started_at", "ended_at", "registered_at", "signed_at", "birth_date"):
                if field in row and row[field] is not None and not _is_date(row[field]):
                    r.error(f"{where}: {field} не дата ISO 8601")
            if (
                row.get("ended_at")
                and row.get("started_at")
                and row["ended_at"] < row["started_at"]
            ):
                r.error(f"{where}: ended_at раньше started_at")
    for row in rows["companies"]:
        if not is_valid_inn(row["inn"]) or not is_valid_ogrn(row["ogrn"]):
            r.error(f"companies.json: {row['name']}: неверная контрольная сумма ИНН/ОГРН")
    for row in rows["persons"]:
        if row["inn"] is not None and not is_valid_inn(row["inn"]):
            r.error(f"persons.json: {row['full_name']}: неверная контрольная сумма ИНН")
    for row in rows["organs"]:
        if not is_valid_inn(row["inn"]):
            r.error(f"organs.json: {row['name']}: неверная контрольная сумма ИНН")
    for row in rows["contracts"]:
        if row["amount"] <= 0:
            r.error(f"contracts.json: {row['reg_number']}: сумма не положительна")
    for row in rows["appeals"]:
        try:
            datetime.fromisoformat(row["received_at"])
        except ValueError:
            r.error(f"appeals.json: {row['id']}: received_at не дата-время")
        if row["status"] != "new" and row["analysis"] is None:
            r.error(f"appeals.json: {row['id']}: статус {row['status']} без analysis")


def check_references(rows: dict[str, list[dict[str, Any]]], r: Report) -> None:
    ids = {name: {row["id"] for row in items} for name, items in rows.items()}
    for name, refs in REFERENCES.items():
        for index, row in enumerate(rows[name], start=1):
            for field, target in refs.items():
                if row[field] not in ids[target]:
                    r.error(f"{name}.json: запись {index}: {field} не найден в {target}.json")
    for row in rows["appeals"]:
        for pid in row["linked_person_ids"]:
            if pid not in ids["persons"]:
                r.error(f"appeals.json: {row['id']}: linked_person_ids {pid} не найден")
    for row in rows["kinships"]:
        if row["person_id"] == row["relative_id"]:
            r.error(f"kinships.json: {row['id']}: родство с самим собой")


def check_truth(rows: dict[str, list[dict[str, Any]]], truth: dict[str, Any], r: Report) -> None:
    if not truth:
        r.warn("_truth/ не найден: проверка разметки пропущена")
        return
    all_ids = {row["id"] for items in rows.values() for row in items}
    officials = {row["person_id"] for row in rows["appointments"]}
    for scheme in truth.get("schemes", []):
        if scheme["person_id"] not in officials:
            r.error(f"_truth/schemes: {scheme['case_id']}: служащий не найден")
        missing = [i for i in scheme["evidence_ids"] if i not in all_ids]
        if missing:
            r.error(f"_truth/schemes: {scheme['case_id']}: нет объектов {missing}")
    appeal_ids = {row["id"] for row in rows["appeals"]}
    labels = truth.get("appeals_labels", [])
    if {label["appeal_id"] for label in labels} != appeal_ids:
        r.error("_truth/appeals_labels: разметка не совпадает со списком обращений")
    for label in labels:
        for pid in label["linked_person_ids"] + label.get("candidate_person_ids", []):
            if pid not in officials:
                r.error(f"_truth/appeals_labels: {label['appeal_id']}: {pid} не служащий")
    for item in truth.get("peer_anomalies", []):
        if item["person_id"] not in officials:
            r.error("_truth/peer_anomalies: служащий не найден")


def check_demo(rows: dict[str, list[dict[str, Any]]], r: Report) -> None:
    by_name = {row["full_name"]: row for row in rows["persons"]}
    officials = {row["person_id"] for row in rows["appointments"]}
    for case, name in DEMO.items():
        person = by_name.get(name)
        if person is None or person["id"] not in officials:
            r.error(f"демо-кейс {case}: служащий {name} не найден")
    companies = {row["name"]: row for row in rows["companies"]}
    dsr = companies.get("ООО «ДорСтройРесурс»")
    if dsr is None:
        r.error("демо-кейс H1: нет ООО «ДорСтройРесурс»")
        return
    contracts = [c for c in rows["contracts"] if c["supplier_company_id"] == dsr["id"]]
    total = sum(c["amount"] for c in contracts)
    if len(contracts) != 5 or not 35e6 <= total <= 40e6:
        r.error(
            f"демо-кейс H1: {len(contracts)} контрактов на {total:,.0f} ₽ (ожидалось 5, ~38 млн)"
        )
    for name in (
        "ООО «МедТехСнаб»",
        "ООО «ЖилКомСервис»",
        "ООО «ФармЛогистик»",
        "ООО «Чистый Двор»",
    ):
        if name not in companies:
            r.error(f"демо-кейс: нет {name}")
    if not any("Соколов Андрей Викторович" in a["text"] for a in rows["appeals"]):
        r.error("демо-кейс H1: нет текста демо-обращения")


def check_distributions(rows: dict[str, list[dict[str, Any]]], r: Report) -> dict[str, Any]:
    for name, (low, high) in VOLUMES.items():
        if not low <= len(rows[name]) <= high:
            r.warn(f"объём {name}: {len(rows[name])}, ожидалось {low}–{high}")
    current = {a["person_id"] for a in rows["appointments"] if a["ended_at"] is None}
    former = {a["person_id"] for a in rows["appointments"]} - current
    if not 130 <= len(current) <= 170:
        r.warn(f"служащих {len(current)}, ожидалось ~150")
    methods = Counter(c["method"] for c in rows["contracts"])
    single = methods["single_supplier"] / max(1, len(rows["contracts"]))
    relatives = Counter(k["person_id"] for k in rows["kinships"])
    per_official = sum(relatives.values()) / max(1, len(current | former))
    liquidated = sum(c["status"] == "liquidated" for c in rows["companies"]) / len(
        rows["companies"]
    )
    return {
        "служащие": len(current),
        "бывшие служащие": len(former),
        "доли способов закупки": {
            k: round(v / len(rows["contracts"]), 3) for k, v in methods.items()
        },
        "единственный поставщик": round(single, 3),
        "родственников на служащего": round(per_official, 2),
        "доля ликвидированных компаний": round(liquidated, 3),
    }


def run(directory: Path, partial: bool = False) -> Report:
    report = Report()
    rows, truth = load(directory)
    check_schema(rows, report)
    check_references(rows, report)
    if partial:  # sample/: связная выборка без разметки, объёмов и всех кейсов
        return report
    check_truth(rows, truth, report)
    check_demo(rows, report)
    stats = check_distributions(rows, report)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return report


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    partial = "--partial" in sys.argv
    directory = Path(args[0] if args else "data/generated")
    print(f"Проверка {directory}" + (" (выборка)" if partial else ""))
    report = run(directory, partial)
    for warning in report.warnings:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {warning}")
    for error in report.errors:
        print(f"ОШИБКА: {error}")
    if report.errors:
        print(f"data-check: {len(report.errors)} ошибок")
        sys.exit(1)
    print("data-check: OK")


if __name__ == "__main__":
    main()
