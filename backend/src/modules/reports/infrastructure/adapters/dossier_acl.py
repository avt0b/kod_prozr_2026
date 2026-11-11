"""ACL reports -> officials + risk: собрать досье служащего.

Источники описаны локальными протоколами; настоящие объекты (QueryOfficialsUseCase,
QueryRiskUseCase) подставляет src/web/dependencies.py.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.reports.application.interfaces.dossier_source import DossierSourceInterface
from src.modules.reports.domain.dossier import Dossier, FlagSummary


class ExternalPerson(Protocol):
    @property
    def full_name(self) -> str: ...


class ExternalPosition(Protocol):
    @property
    def title(self) -> str: ...
    @property
    def department(self) -> str: ...


class ExternalOrgan(Protocol):
    @property
    def name(self) -> str: ...


class ExternalAppointment(Protocol):
    @property
    def position(self) -> ExternalPosition: ...
    @property
    def organ(self) -> ExternalOrgan: ...
    @property
    def started_at(self) -> date: ...


class ExternalSnapshot(Protocol):
    @property
    def person(self) -> ExternalPerson: ...
    @property
    def current_appointment(self) -> ExternalAppointment | None: ...


class ExternalOfficialsSource(Protocol):
    async def snapshots(self, person_ids: Sequence[UUID]) -> Sequence[ExternalSnapshot]: ...


class ExternalEvidence(Protocol):
    @property
    def label(self) -> str: ...


class ExternalFlag(Protocol):
    @property
    def rule_code(self) -> str: ...
    @property
    def rule_name(self) -> str: ...
    @property
    def severity(self) -> str: ...
    @property
    def weight(self) -> float: ...
    @property
    def explanation(self) -> str: ...
    @property
    def legal_ref(self) -> str | None: ...
    @property
    def evidence(self) -> Sequence[ExternalEvidence]: ...


class ExternalScore(Protocol):
    @property
    def score(self) -> float: ...


class ExternalRiskSource(Protocol):
    async def get_scores(self, person_ids: Sequence[UUID]) -> Sequence[ExternalScore]: ...

    async def get_flags(self, person_ids: Sequence[UUID]) -> Sequence[ExternalFlag]: ...


class DossierACLAdapter(DossierSourceInterface):
    def __init__(self, officials: ExternalOfficialsSource, risk: ExternalRiskSource) -> None:
        self._officials = officials
        self._risk = risk

    async def get_dossier(self, person_id: UUID) -> Dossier | None:
        snapshots = await self._officials.snapshots([person_id])
        if not snapshots:
            return None
        snapshot = snapshots[0]
        appointment = snapshot.current_appointment
        scores = await self._risk.get_scores([person_id])
        flags = sorted(await self._risk.get_flags([person_id]), key=lambda f: -f.weight)
        return Dossier(
            person_id=person_id,
            full_name=snapshot.person.full_name,
            position_title=appointment.position.title if appointment else None,
            department=appointment.position.department if appointment else None,
            organ_name=appointment.organ.name if appointment else None,
            appointed_at=appointment.started_at if appointment else None,
            score=scores[0].score if scores else 0.0,
            flags=tuple(
                FlagSummary(
                    rule_code=f.rule_code,
                    rule_name=f.rule_name,
                    severity=f.severity,
                    explanation=f.explanation,
                    legal_ref=f.legal_ref,
                    evidence=tuple(e.label for e in f.evidence),
                )
                for f in flags
            ),
        )
