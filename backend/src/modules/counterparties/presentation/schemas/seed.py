"""Формат JSON-файлов синтетики для контекста counterparties."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from src.modules.counterparties.domain.company import Company, CompanyRole
from src.modules.counterparties.domain.contract import Contract
from src.modules.counterparties.domain.enums import CompanyRoleKind, CompanyStatus


class CompanySeed(BaseModel):
    id: UUID
    inn: str
    ogrn: str
    name: str
    okved: str
    address: str | None = None
    phone: str | None = None
    registered_at: date | None = None
    status: CompanyStatus = CompanyStatus.ACTIVE

    def to_entity(self) -> Company:
        return Company(**self.model_dump())


class CompanyRoleSeed(BaseModel):
    id: UUID
    company_id: UUID
    person_id: UUID
    role: CompanyRoleKind
    share: float | None = None
    started_at: date
    ended_at: date | None = None

    def to_entity(self) -> CompanyRole:
        return CompanyRole(**self.model_dump())


class ContractSeed(BaseModel):
    id: UUID
    reg_number: str
    customer_organ_id: UUID
    supplier_company_id: UUID
    amount: float
    signed_at: date
    okpd2: str | None = None
    method: str | None = None

    def to_entity(self) -> Contract:
        return Contract(**self.model_dump())
