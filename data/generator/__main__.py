"""CLI генератора синтетики (docs/data.md §3).

    python -m data.generator --seed 42 --out data/generated/ [--threshold 600000]

Пишет один JSON на сущность контракта, `_truth/` с разметкой и `sample/` — согласованную
выборку вокруг демо-кейсов (по 5–15 записей) для быстрых проверок.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from data.generator.appeals import AppealsBuilder
from data.generator.cases import Scenario
from data.generator.world import WorldBuilder

ENTITIES = (
    "organs", "positions", "authorities", "persons", "appointments", "kinships",
    "companies", "company_roles", "employments", "contracts", "appeals",
)  # fmt: skip
SAMPLE_CASES = ("H1", "C2", "C3", "C5", "N1")


def generate(
    seed: int, threshold: float
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], Scenario]:
    world = WorldBuilder(seed, threshold)
    scenario = Scenario(world)
    scenario.build()
    appeals = AppealsBuilder(scenario)
    world.rows["appeals"] = appeals.build()
    truth = scenario.truth()
    truth["appeals_labels"] = appeals.labels
    truth["meta"] = {
        "seed": seed,
        "threshold": threshold,
        "cases": {case: o.person_id for case, o in sorted(scenario.cases.items())},
        "demo_appeal_ids": [label["appeal_id"] for label in appeals.labels if label["keep_new"]],
    }
    rows = {name: world.rows[name] for name in ENTITIES}
    return rows, truth, scenario


def sample(
    rows: dict[str, list[dict[str, Any]]], scenario: Scenario
) -> dict[str, list[dict[str, Any]]]:
    """Связная выборка вокруг кейсов SAMPLE_CASES: проходит те же проверки, что полный набор."""
    officials = {scenario.cases[c].person_id for c in SAMPLE_CASES}
    kin = [k for k in rows["kinships"] if k["person_id"] in officials]
    people = officials | {k["relative_id"] for k in kin}
    roles = [r for r in rows["company_roles"] if r["person_id"] in people]
    companies = {r["company_id"] for r in roles}
    employments = [e for e in rows["employments"] if e["person_id"] in officials]
    companies |= {e["company_id"] for e in employments}
    contracts = [c for c in rows["contracts"] if c["supplier_company_id"] in companies][:15]
    roles += [r for r in rows["company_roles"] if r["company_id"] in companies and r not in roles][
        :10
    ]
    people |= {r["person_id"] for r in roles}
    appointments = [a for a in rows["appointments"] if a["person_id"] in officials]
    positions = {a["position_id"] for a in appointments}
    appeals = [a for a in rows["appeals"] if "Соколов" in a["text"] or "Орлов" in a["text"]]
    appeals += [a for a in rows["appeals"] if a not in appeals][:3]
    return {
        "organs": rows["organs"],
        "positions": [p for p in rows["positions"] if p["id"] in positions],
        "authorities": [a for a in rows["authorities"] if a["position_id"] in positions],
        "persons": [p for p in rows["persons"] if p["id"] in people],
        "appointments": appointments,
        "kinships": kin,
        "companies": [c for c in rows["companies"] if c["id"] in companies],
        "company_roles": [r for r in roles if r["person_id"] in people],
        "employments": employments,
        "contracts": contracts,
        "appeals": appeals,
    }


def write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m data.generator", description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/generated")
    parser.add_argument(
        "--threshold",
        type=float,
        default=600_000,
        help="порог «закупки чуть ниже порога», ₽ (тот же параметр в R08 бэкенда)",
    )
    args = parser.parse_args()
    out = Path(args.out)
    rows, truth, scenario = generate(args.seed, args.threshold)
    for name, items in rows.items():
        write(out / f"{name}.json", items)
    write(out / "_truth" / "schemes.json", truth["schemes"])
    write(out / "_truth" / "appeals_labels.json", truth["appeals_labels"])
    write(out / "_truth" / "peer_anomalies.json", truth["peer_anomalies"])
    write(out / "_truth" / "meta.json", truth["meta"])
    for name, items in sample(rows, scenario).items():
        write(out / "sample" / f"{name}.json", items)
    officials = {a["person_id"] for a in rows["appointments"]}
    print(
        f"Сгенерировано в {out}: "
        + ", ".join(f"{name} {len(items)}" for name, items in rows.items())
        + f"; служащих {len(officials)}, схем {len(truth['schemes'])}"
    )


if __name__ == "__main__":
    main()
