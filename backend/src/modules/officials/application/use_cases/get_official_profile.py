from uuid import UUID

from src.modules.officials.application.dto.officials_dto import OfficialProfileDTO
from src.modules.officials.application.interfaces.company_links_source import (
    CompanyLinksSourceInterface,
)
from src.modules.officials.application.interfaces.risk_source import RiskSourceInterface
from src.modules.officials.application.use_cases.get_official_snapshots import (
    GetOfficialSnapshotsUseCase,
)
from src.modules.officials.domain.exceptions import OfficialNotFoundError


class GetOfficialProfileUseCase:
    """Профиль служащего: человек, назначения, полномочия, родственники,
    компании (его и родственников), риск."""

    def __init__(
        self,
        snapshots: GetOfficialSnapshotsUseCase,
        company_links: CompanyLinksSourceInterface,
        risk_source: RiskSourceInterface,
    ) -> None:
        self._snapshots = snapshots
        self._company_links = company_links
        self._risk = risk_source

    async def execute(self, person_id: UUID) -> OfficialProfileDTO:
        found = await self._snapshots.execute([person_id])
        if not found:
            raise OfficialNotFoundError(person_id)
        snapshot = found[0]

        linked_person_ids = [person_id, *(r.person.id for r in snapshot.relatives)]
        companies = await self._company_links.get_links(linked_person_ids)
        risk = await self._risk.get_official_risk(person_id)

        authorities = tuple(
            authority
            for appointment in snapshot.appointments
            if appointment.is_active
            for authority in appointment.authorities
        )
        return OfficialProfileDTO(
            person=snapshot.person,
            appointments=snapshot.appointments,
            authorities=authorities,
            relatives=snapshot.relatives,
            companies=tuple(companies),
            employments=snapshot.employments,
            risk=risk,
        )
