"""ACL risk -> counterparties."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.risk.application.interfaces.counterparties_source import (
    CounterpartiesSourceInterface,
)
from src.modules.risk.domain.facts import CompanyFacts, CompanyRoleFacts, ContractFacts


class ExternalCompany(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def name(self) -> str: ...
    @property
    def inn(self) -> str: ...
    @property
    def status(self) -> str: ...
    @property
    def okved(self) -> str: ...
    @property
    def address(self) -> str | None: ...
    @property
    def phone(self) -> str | None: ...


class ExternalCompanyRole(Protocol):
    @property
    def company_id(self) -> UUID: ...
    @property
    def person_id(self) -> UUID: ...
    @property
    def role(self) -> str: ...
    @property
    def share(self) -> float | None: ...
    @property
    def started_at(self) -> date: ...
    @property
    def ended_at(self) -> date | None: ...


class ExternalContract(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def reg_number(self) -> str: ...
    @property
    def customer_organ_id(self) -> UUID: ...
    @property
    def supplier_company_id(self) -> UUID: ...
    @property
    def amount(self) -> float: ...
    @property
    def signed_at(self) -> date: ...
    @property
    def okpd2(self) -> str | None: ...


class ExternalCounterpartiesSource(Protocol):
    async def companies(self, company_ids: Sequence[UUID]) -> Sequence[ExternalCompany]: ...

    async def all_companies(self, limit: int = ...) -> Sequence[ExternalCompany]: ...

    async def roles_for_persons(
        self, person_ids: Sequence[UUID]
    ) -> Sequence[ExternalCompanyRole]: ...

    async def roles_for_companies(
        self, company_ids: Sequence[UUID]
    ) -> Sequence[ExternalCompanyRole]: ...

    async def contracts(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int = ...,
    ) -> Sequence[ExternalContract]: ...


def _company(company: ExternalCompany) -> CompanyFacts:
    return CompanyFacts(
        id=company.id,
        name=company.name,
        inn=company.inn,
        status=company.status,
        okved=company.okved,
        address=company.address,
        phone=company.phone,
    )


def _role(role: ExternalCompanyRole) -> CompanyRoleFacts:
    return CompanyRoleFacts(
        company_id=role.company_id,
        person_id=role.person_id,
        role=role.role,
        started_at=role.started_at,
        ended_at=role.ended_at,
        share=role.share,
    )


class CounterpartiesACLAdapter(CounterpartiesSourceInterface):
    def __init__(self, external_source: ExternalCounterpartiesSource) -> None:
        self._source = external_source

    async def roles_for_persons(self, person_ids: Sequence[UUID]) -> list[CompanyRoleFacts]:
        return [_role(r) for r in await self._source.roles_for_persons(person_ids)]

    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> list[CompanyRoleFacts]:
        return [_role(r) for r in await self._source.roles_for_companies(company_ids)]

    async def companies(self, company_ids: Sequence[UUID]) -> list[CompanyFacts]:
        return [_company(c) for c in await self._source.companies(company_ids)]

    async def all_companies(self, limit: int) -> list[CompanyFacts]:
        return [_company(c) for c in await self._source.all_companies(limit)]

    async def contracts(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int,
    ) -> list[ContractFacts]:
        found = await self._source.contracts(
            customer_organ_ids=customer_organ_ids,
            supplier_company_ids=supplier_company_ids,
            limit=limit,
        )
        return [
            ContractFacts(
                id=c.id,
                reg_number=c.reg_number,
                customer_organ_id=c.customer_organ_id,
                supplier_company_id=c.supplier_company_id,
                amount=c.amount,
                signed_at=c.signed_at,
                okpd2=c.okpd2,
            )
            for c in found
        ]
