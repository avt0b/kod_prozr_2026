from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from src.core.infrastructure.interfaces.audit_log import AuditLogInterface
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.officials.application.dto.officials_dto import (
    CompanyLinkDTO,
    ContractView,
    OfficialProfileDTO,
    OfficialSnapshotDTO,
)
from src.modules.officials.application.interfaces.company_links_source import (
    CompanyLinksSourceInterface,
)
from src.modules.officials.application.interfaces.risk_source import RiskSourceInterface
from src.modules.officials.application.use_cases.get_official_snapshots import (
    GetOfficialSnapshotsUseCase,
)
from src.modules.officials.domain.exceptions import OfficialNotFoundError

SELF = "self"
EMPLOYEE = "employee"


@dataclass
class _Totals:
    count: int = 0
    amount: float = 0.0


_NO_CONTRACTS = _Totals()


class GetOfficialProfileUseCase:
    """Профиль служащего: человек, назначения, полномочия, родственники, компании, риск.

    Компании — роли учредителя и директора самого служащего и его родственников, плюс места
    работы служащего (role = employee). У каждой — число и сумма контрактов с органами, где
    служащий замещал должность, заключённых в период замещения (contracts.md, как в R01).
    """

    def __init__(
        self,
        snapshots: GetOfficialSnapshotsUseCase,
        company_links: CompanyLinksSourceInterface,
        risk_source: RiskSourceInterface,
        audit: AuditLogInterface | None = None,
        unit_of_work: UnitOfWorkInterface | None = None,
    ) -> None:
        self._snapshots = snapshots
        self._company_links = company_links
        self._risk = risk_source
        self._audit = audit
        self._unit_of_work = unit_of_work

    async def execute(self, person_id: UUID) -> OfficialProfileDTO:
        found = await self._snapshots.execute([person_id])
        if not found:
            raise OfficialNotFoundError(person_id)
        snapshot = found[0]

        companies = await self._companies(snapshot)
        risk = await self._risk.get_official_risk(person_id)
        authorities = tuple(
            authority
            for appointment in snapshot.appointments
            if appointment.is_active
            for authority in appointment.authorities
        )
        if self._audit and self._unit_of_work:
            async with self._unit_of_work:
                await self._audit.record("open_profile", "person", person_id)
                await self._unit_of_work.commit()
        return OfficialProfileDTO(
            person=snapshot.person,
            appointments=snapshot.appointments,
            authorities=authorities,
            relatives=snapshot.relatives,
            companies=companies,
            employments=snapshot.employments,
            risk=risk,
        )

    async def _companies(self, snapshot: OfficialSnapshotDTO) -> tuple[CompanyLinkDTO, ...]:
        official = snapshot.person
        relation = {official.id: SELF} | {r.person.id: r.kind for r in snapshot.relatives}
        names = {official.id: official.full_name} | {
            r.person.id: r.person.full_name for r in snapshot.relatives
        }

        roles = await self._company_links.get_roles(list(relation))
        employers = {
            c.id: c
            for c in await self._company_links.get_companies(
                list({e.company_id for e in snapshot.employments})
            )
        }
        company_ids = list({r.company.id for r in roles} | set(employers))
        organ_ids = list({a.organ.id for a in snapshot.appointments})
        contracts = await self._company_links.contracts(organ_ids, company_ids)
        totals = _tenure_totals(snapshot, contracts)

        links = [
            CompanyLinkDTO(
                company=role.company,
                role=role.role,
                share=role.share,
                via_person_id=role.person_id,
                via_person_name=names[role.person_id],
                relation=relation[role.person_id],
                started_at=role.started_at,
                ended_at=role.ended_at,
                contracts_count=totals.get(role.company.id, _NO_CONTRACTS).count,
                contracts_amount=totals.get(role.company.id, _NO_CONTRACTS).amount,
            )
            for role in roles
            if role.person_id in relation
        ]
        links += [
            CompanyLinkDTO(
                company=employers[e.company_id],
                role=EMPLOYEE,
                share=None,
                via_person_id=official.id,
                via_person_name=official.full_name,
                relation=SELF,
                started_at=e.started_at,
                ended_at=e.ended_at,
                contracts_count=totals.get(e.company_id, _NO_CONTRACTS).count,
                contracts_amount=totals.get(e.company_id, _NO_CONTRACTS).amount,
            )
            for e in snapshot.employments
            if e.company_id in employers
        ]
        # Сначала то, что ближе к риску: больше денег от органов служащего, затем свои связи.
        links.sort(key=lambda link: (-link.contracts_amount, link.relation != SELF))
        return tuple(links)


def _tenure_totals(
    snapshot: OfficialSnapshotDTO, contracts: list[ContractView]
) -> dict[UUID, _Totals]:
    totals: dict[UUID, _Totals] = defaultdict(_Totals)
    for contract in contracts:
        in_tenure = any(
            a.organ.id == contract.customer_organ_id
            and a.started_at <= contract.signed_at
            and (a.ended_at is None or contract.signed_at <= a.ended_at)
            for a in snapshot.appointments
        )
        if in_tenure:
            total = totals[contract.supplier_company_id]
            total.count += 1
            total.amount += contract.amount
    return totals
