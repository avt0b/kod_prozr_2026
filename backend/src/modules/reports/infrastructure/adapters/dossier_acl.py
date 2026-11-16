"""ACL reports -> officials + risk: собрать досье служащего.

Источники описаны локальными протоколами; настоящие объекты (QueryOfficialsUseCase,
QueryRiskUseCase) подставляет src/web/dependencies.py.
"""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from src.modules.reports.application.interfaces.dossier_source import DossierSourceInterface
from src.modules.reports.domain.dossier import AppealSummary, Dossier, FlagSummary


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


class ExternalAuthority(Protocol):
    @property
    def kind(self) -> str: ...
    @property
    def okpd2(self) -> Sequence[str]: ...


class ExternalAppointment(Protocol):
    @property
    def position(self) -> ExternalPosition: ...
    @property
    def organ(self) -> ExternalOrgan: ...
    @property
    def started_at(self) -> date: ...
    @property
    def ended_at(self) -> date | None: ...
    @property
    def authorities(self) -> Sequence[ExternalAuthority]: ...


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


class ExternalAppeal(Protocol):
    @property
    def appeal_id(self) -> UUID: ...
    @property
    def received_at(self) -> datetime: ...
    @property
    def summary(self) -> str | None: ...
    @property
    def specificity(self) -> float: ...
    @property
    def category(self) -> str | None: ...


class ExternalAppealsSource(Protocol):
    async def mentions(self, person_ids: Sequence[UUID]) -> Sequence[ExternalAppeal]: ...


class DossierACLAdapter(DossierSourceInterface):
    def __init__(
        self,
        officials: ExternalOfficialsSource,
        risk: ExternalRiskSource,
        appeals: ExternalAppealsSource,
    ) -> None:
        self._officials = officials
        self._risk = risk
        self._appeals = appeals

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
            ended_at=appointment.ended_at if appointment else None,
            authorities=tuple(
                {
                    "procurement": "закупки",
                    "permits": "разрешения",
                    "inspection": "проверки",
                    "budget": "бюджет",
                    "hr": "кадры",
                }.get(a.kind, a.kind)
                + (f" (ОКПД2: {', '.join(a.okpd2)})" if a.okpd2 else "")
                for a in (appointment.authorities if appointment else ())
            ),
            appeals=tuple(
                AppealSummary(
                    a.appeal_id,
                    a.received_at.strftime("%d.%m.%Y"),
                    a.summary or "Без краткого содержания",
                    a.specificity,
                    a.category,
                )
                for a in sorted(
                    await self._appeals.mentions([person_id]), key=lambda m: m.received_at
                )
            ),
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
