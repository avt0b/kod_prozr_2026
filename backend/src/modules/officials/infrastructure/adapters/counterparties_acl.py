"""ACL officials -> counterparties: компании, связанные с человеком."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import CompanyLinkView
from src.modules.officials.application.interfaces.company_links_source import (
    CompanyLinksSourceInterface,
)


class ExternalCompany(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def name(self) -> str: ...
    @property
    def inn(self) -> str: ...
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


class ExternalCompanySource(Protocol):
    async def roles_for_persons(
        self, person_ids: Sequence[UUID]
    ) -> Sequence[ExternalCompanyRole]: ...

    async def companies(self, company_ids: Sequence[UUID]) -> Sequence[ExternalCompany]: ...


class CounterpartiesACLAdapter(CompanyLinksSourceInterface):
    def __init__(self, external_source: ExternalCompanySource) -> None:
        self._source = external_source

    async def get_links(self, person_ids: Sequence[UUID]) -> list[CompanyLinkView]:
        roles = await self._source.roles_for_persons(person_ids)
        companies = {
            c.id: c for c in await self._source.companies(list({r.company_id for r in roles}))
        }
        links: list[CompanyLinkView] = []
        for role in roles:
            company = companies.get(role.company_id)
            if company is None:
                continue
            links.append(
                CompanyLinkView(
                    person_id=role.person_id,
                    company_id=company.id,
                    company_name=company.name,
                    company_inn=company.inn,
                    company_status=company.status,
                    role=role.role,
                    share=role.share,
                    started_at=role.started_at,
                    ended_at=role.ended_at,
                )
            )
        return links
