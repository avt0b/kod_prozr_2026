"""ACL officials -> counterparties: компании, роли людей в них и итоги контрактов."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import (
    CompanyRoleView,
    CompanyView,
    ContractView,
)
from src.modules.officials.application.interfaces.company_links_source import (
    CompanyLinksSourceInterface,
)

MAX_CONTRACTS = 100_000


class ExternalCompany(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def inn(self) -> str: ...
    @property
    def ogrn(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def okved(self) -> str: ...
    @property
    def address(self) -> str | None: ...
    @property
    def phone(self) -> str | None: ...
    @property
    def registered_at(self) -> date | None: ...
    @property
    def status(self) -> str: ...


class ExternalCompanyRole(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def company_id(self) -> UUID: ...
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
    def supplier_company_id(self) -> UUID: ...
    @property
    def customer_organ_id(self) -> UUID: ...
    @property
    def amount(self) -> float: ...
    @property
    def signed_at(self) -> date: ...


class ExternalCompanySource(Protocol):
    async def roles_for_persons(
        self, person_ids: Sequence[UUID]
    ) -> Sequence[ExternalCompanyRole]: ...

    async def companies(self, company_ids: Sequence[UUID]) -> Sequence[ExternalCompany]: ...

    async def contracts(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int = ...,
    ) -> Sequence[ExternalContract]: ...


def _company(company: ExternalCompany) -> CompanyView:
    return CompanyView(
        id=company.id,
        inn=company.inn,
        ogrn=company.ogrn,
        name=company.name,
        okved=company.okved,
        address=company.address,
        phone=company.phone,
        registered_at=company.registered_at,
        status=company.status,
    )


class CounterpartiesACLAdapter(CompanyLinksSourceInterface):
    def __init__(self, external_source: ExternalCompanySource) -> None:
        self._source = external_source

    async def get_roles(self, person_ids: Sequence[UUID]) -> list[CompanyRoleView]:
        roles = await self._source.roles_for_persons(person_ids)
        companies = {c.id: c for c in await self.get_companies(list({r.company_id for r in roles}))}
        return [
            CompanyRoleView(
                person_id=role.person_id,
                company=companies[role.company_id],
                role=role.role,
                share=role.share,
                started_at=role.started_at,
                ended_at=role.ended_at,
            )
            for role in roles
            if role.company_id in companies
        ]

    async def get_companies(self, company_ids: Sequence[UUID]) -> list[CompanyView]:
        if not company_ids:
            return []
        return [_company(c) for c in await self._source.companies(company_ids)]

    async def contracts(
        self, organ_ids: Sequence[UUID], company_ids: Sequence[UUID]
    ) -> list[ContractView]:
        if not organ_ids or not company_ids:
            return []
        found = await self._source.contracts(
            customer_organ_ids=organ_ids, supplier_company_ids=company_ids, limit=MAX_CONTRACTS
        )
        return [
            ContractView(
                supplier_company_id=c.supplier_company_id,
                customer_organ_id=c.customer_organ_id,
                amount=c.amount,
                signed_at=c.signed_at,
            )
            for c in found
        ]
