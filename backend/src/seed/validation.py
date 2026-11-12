"""Validate a complete seed snapshot before changing the database."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.core.exceptions import DomainError
from src.core.utils.json_files import read_models
from src.modules.appeals.presentation.schemas.seed import AppealSeed
from src.modules.counterparties.presentation.schemas.seed import (
    CompanyRoleSeed,
    CompanySeed,
    ContractSeed,
)
from src.modules.officials.presentation.schemas.seed import (
    AppointmentSeed,
    AuthoritySeed,
    EmploymentSeed,
    KinshipSeed,
    OrganSeed,
    PersonSeed,
    PositionSeed,
)

SCHEMAS: dict[str, type[BaseModel]] = {
    "organs": OrganSeed,
    "persons": PersonSeed,
    "positions": PositionSeed,
    "authorities": AuthoritySeed,
    "appointments": AppointmentSeed,
    "kinships": KinshipSeed,
    "employments": EmploymentSeed,
    "companies": CompanySeed,
    "company_roles": CompanyRoleSeed,
    "contracts": ContractSeed,
    "appeals": AppealSeed,
}
REFERENCES = {
    "positions": {"organ_id": "organs"},
    "authorities": {"position_id": "positions"},
    "appointments": {"person_id": "persons", "position_id": "positions"},
    "kinships": {"person_id": "persons", "relative_id": "persons"},
    "employments": {"person_id": "persons", "company_id": "companies"},
    "company_roles": {"person_id": "persons", "company_id": "companies"},
    "contracts": {"customer_organ_id": "organs", "supplier_company_id": "companies"},
}


def validate_snapshot(data_dir: Path) -> None:
    rows: dict[str, list[dict[str, Any]]] = {}
    for name, schema in SCHEMAS.items():
        path = data_dir / f"{name}.json"
        if not path.is_file():
            raise ValueError(f"{path}: required seed file is missing")
        models = read_models(schema, path)
        for index, model in enumerate(models, start=1):
            try:
                # Domain invariants (periods, nonempty appeal text, etc.).
                getattr(model, "to_entity")()
            except (ValueError, DomainError) as exc:
                raise ValueError(f"{path}: record {index}: invalid domain data") from exc
        rows[name] = [model.model_dump() for model in models]
        ids = [row["id"] for row in rows[name]]
        seen = set()
        for index, record_id in enumerate(ids, start=1):
            if record_id in seen:
                raise ValueError(f"{path}: record {index}: duplicate id")
            seen.add(record_id)
    ids_by_name = {name: {row["id"] for row in items} for name, items in rows.items()}
    for name, references in REFERENCES.items():
        for index, row in enumerate(rows[name], start=1):
            for field, target in references.items():
                if row[field] not in ids_by_name[target]:
                    raise ValueError(f"{data_dir / name}.json: record {index}: unknown {field}")
    for index, row in enumerate(rows["appeals"], start=1):
        if not set(row["linked_person_ids"]) <= ids_by_name["persons"]:
            raise ValueError(
                f"{data_dir / 'appeals.json'}: record {index}: unknown linked_person_ids"
            )
