from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.modules.counterparties.domain.company import Company, CompanyRole
from src.modules.counterparties.domain.contract import Contract


@dataclass(frozen=True)
class CompanyDTO:
    id: UUID
    inn: str
    ogrn: str
    name: str
    okved: str
    address: str | None
    phone: str | None
    registered_at: date | None
    status: str

    @classmethod
    def from_entity(cls, company: Company) -> "CompanyDTO":
        return cls(
            id=company.id,
            inn=company.inn,
            ogrn=company.ogrn,
            name=company.name,
            okved=company.okved,
            address=company.address,
            phone=company.phone,
            registered_at=company.registered_at,
            status=company.status.value,
        )


@dataclass(frozen=True)
class CompanyRoleDTO:
    id: UUID
    company_id: UUID
    person_id: UUID
    role: str
    share: float | None
    started_at: date
    ended_at: date | None

    @classmethod
    def from_entity(cls, role: CompanyRole) -> "CompanyRoleDTO":
        return cls(
            id=role.id,
            company_id=role.company_id,
            person_id=role.person_id,
            role=role.role.value,
            share=role.share,
            started_at=role.started_at,
            ended_at=role.ended_at,
        )


@dataclass(frozen=True)
class ContractDTO:
    id: UUID
    reg_number: str
    customer_organ_id: UUID
    supplier_company_id: UUID
    amount: float
    signed_at: date
    okpd2: str | None
    method: str | None

    @classmethod
    def from_entity(cls, contract: Contract) -> "ContractDTO":
        return cls(
            id=contract.id,
            reg_number=contract.reg_number,
            customer_organ_id=contract.customer_organ_id,
            supplier_company_id=contract.supplier_company_id,
            amount=contract.amount,
            signed_at=contract.signed_at,
            okpd2=contract.okpd2,
            method=contract.method,
        )
