from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from src.core.utils.text import format_rub
from src.modules.assistant.application.interfaces.tools import ToolArguments, ToolItem, ToolName


class Person(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def full_name(self) -> str: ...


class Organ(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def name(self) -> str: ...


class Position(Protocol):
    @property
    def title(self) -> str: ...


class Appointment(Protocol):
    @property
    def organ(self) -> Organ: ...
    @property
    def position(self) -> Position: ...


class Snapshot(Protocol):
    @property
    def person(self) -> Person: ...
    @property
    def current_appointment(self) -> Appointment | None: ...


class Evidence(Protocol):
    @property
    def type(self) -> str: ...


class Flag(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def rule_code(self) -> str: ...
    @property
    def weight(self) -> float: ...
    @property
    def explanation(self) -> str: ...
    @property
    def evidence(self) -> Sequence[Evidence]: ...


class Score(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def score(self) -> float: ...


class Analysis(Protocol):
    @property
    def summary(self) -> str: ...


class Appeal(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def received_at(self) -> datetime: ...
    @property
    def analysis(self) -> Analysis | None: ...


class Company(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def inn(self) -> str: ...
    @property
    def name(self) -> str: ...


class Role(Protocol):
    @property
    def company_id(self) -> UUID: ...
    @property
    def person_id(self) -> UUID: ...
    @property
    def role(self) -> str: ...
    @property
    def ended_at(self) -> date | None: ...


class Contract(Protocol):
    @property
    def supplier_company_id(self) -> UUID: ...
    @property
    def amount(self) -> float: ...


class OfficialsSource(Protocol):
    async def official_ids(self) -> list[UUID]: ...
    async def snapshots(self, person_ids: Sequence[UUID]) -> Sequence[Snapshot]: ...
    async def persons_by_name(self, name_query: str) -> Sequence[Person]: ...
    async def persons(self, person_ids: Sequence[UUID]) -> Sequence[Person]: ...


class RiskSource(Protocol):
    async def get_scores(self, person_ids: Sequence[UUID]) -> Sequence[Score]: ...
    async def get_flags(self, person_ids: Sequence[UUID]) -> Sequence[Flag]: ...


class AppealsSource(Protocol):
    async def search(
        self, person_id: UUID | None, category: str | None, status: str | None, limit: int
    ) -> Sequence[Appeal]: ...


class CompaniesSource(Protocol):
    async def all_companies(self, limit: int) -> Sequence[Company]: ...
    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> Sequence[Role]: ...
    async def contracts(
        self, *, supplier_company_ids: Sequence[UUID] | None = None, limit: int
    ) -> Sequence[Contract]: ...


class AssistantToolsACL:
    """Read tools over published query ports; no SQL or cross-context model access."""

    def __init__(
        self,
        officials: OfficialsSource,
        risk: RiskSource,
        appeals: AppealsSource,
        companies: CompaniesSource,
    ) -> None:
        self._officials, self._risk = officials, risk
        self._appeals, self._companies = appeals, companies

    async def execute(self, tool: ToolName, args: ToolArguments) -> list[ToolItem]:
        allowed = {
            "search_officials": {"query", "organ_id", "organ_query", "min_score", "limit"},
            "get_profile": {"query", "person_id", "limit"},
            "relatives_among_suppliers": {"organ_id", "organ_query", "min_score", "limit"},
            "top_risk": {"organ_id", "organ_query", "min_score", "limit"},
            "find_appeals": {"query", "person_id", "category", "status", "limit"},
            "company_lookup": {"query", "inn", "limit"},
        }
        if tool not in allowed or any(
            value is not None and field not in allowed[tool]
            for field, value in asdict(args).items()
        ):
            raise ValueError("unsupported tool arguments")
        if not 1 <= args.limit <= 20:
            raise ValueError("limit must be 1..20")
        if tool == "find_appeals":
            return await self._find_appeals(args)
        if tool == "company_lookup":
            return await self._company_lookup(args)
        if tool not in {"search_officials", "get_profile", "relatives_among_suppliers", "top_risk"}:
            raise ValueError("unknown tool")
        if tool == "get_profile" and args.person_id is None and not args.query:
            raise ValueError("person is required")
        ids = [args.person_id] if args.person_id else await self._officials.official_ids()
        if args.query:
            found = _surname_candidates(
                await self._officials.persons_by_name(args.query), args.query
            )
            ids = [person_id for person_id in ids if person_id in {p.id for p in found}]
        snapshots = await self._officials.snapshots(ids)
        if tool == "get_profile" and len(snapshots) != 1:
            raise ValueError("ambiguous person")
        organ_id = args.organ_id
        if args.organ_query:
            organ_id = _resolve_organ(snapshots, args.organ_query)
        if organ_id:
            snapshots = [
                s
                for s in snapshots
                if s.current_appointment and s.current_appointment.organ.id == organ_id
            ]
        ids = [s.person.id for s in snapshots]
        scores = {s.person_id: s.score for s in await self._risk.get_scores(ids)}
        flags = await self._risk.get_flags(ids)
        rows = []
        for snapshot in sorted(
            snapshots, key=lambda s: (-scores.get(s.person.id, 0), s.person.full_name)
        ):
            person = snapshot.person
            own_flags = sorted(
                [f for f in flags if f.person_id == person.id], key=lambda f: -f.weight
            )
            if tool == "relatives_among_suppliers":
                own_flags = [
                    f
                    for f in own_flags
                    if f.rule_code == "R01" and sum(e.type == "person" for e in f.evidence) >= 2
                ]
                if not own_flags:
                    continue
            score = scores.get(person.id, 0)
            if args.min_score is not None and score < args.min_score:
                continue
            appointment = snapshot.current_appointment
            position = (
                f"{appointment.position.title}, {appointment.organ.name}; " if appointment else ""
            )
            facts = (
                "; ".join(f"{f.rule_code}: {f.explanation}" for f in own_flags[:3])
                or "флаги не выявлены"
            )
            rows.append(
                ToolItem(
                    "person",
                    str(person.id),
                    person.full_name,
                    f"{position}риск {score:g}/100; {facts}",
                )
            )
            if len(rows) == args.limit:
                break
        return rows

    async def _find_appeals(self, args: ToolArguments) -> list[ToolItem]:
        person_id = args.person_id
        if args.query:
            found = _surname_candidates(
                await self._officials.persons_by_name(args.query), args.query
            )
            snapshots = await self._officials.snapshots([p.id for p in found])
            if len(snapshots) != 1:
                raise ValueError("ambiguous person")
            person_id = snapshots[0].person.id
        appeals = await self._appeals.search(person_id, args.category, args.status, args.limit)
        return [
            ToolItem(
                "appeal",
                str(a.id),
                f"Обращение от {a.received_at:%d.%m.%Y}",
                a.analysis.summary if a.analysis else "Анализ ещё не выполнен",
            )
            for a in appeals
        ]

    async def _company_lookup(self, args: ToolArguments) -> list[ToolItem]:
        if not args.inn and not args.query:
            raise ValueError("company name or INN required")
        companies = [
            c
            for c in await self._companies.all_companies(limit=100_000)
            if (not args.inn or c.inn == args.inn)
            and (not args.query or args.query.casefold() in c.name.casefold())
        ][: args.limit]
        ids = [c.id for c in companies]
        roles = await self._companies.roles_for_companies(ids)
        people = {
            p.id: p.full_name
            for p in await self._officials.persons(list({r.person_id for r in roles}))
        }
        contracts = await self._companies.contracts(supplier_company_ids=ids, limit=100_000)
        rows = []
        for company in companies:
            own = [c for c in contracts if c.supplier_company_id == company.id]
            owners = "; ".join(
                f"{'учредитель' if r.role == 'founder' else 'директор'}: {people[r.person_id]}"
                + (f" (до {r.ended_at:%d.%m.%Y})" if r.ended_at else "")
                for r in roles
                if r.company_id == company.id and r.person_id in people
            )
            rows.append(
                ToolItem(
                    "company",
                    str(company.id),
                    company.name,
                    f"ИНН {company.inn}; {owners}; контрактов: {len(own)}, "
                    f"сумма {format_rub(sum(c.amount for c in own))}",
                )
            )
        return rows


def _resolve_organ(snapshots: Sequence[Snapshot], query: str) -> UUID:
    names = {
        s.current_appointment.organ.id: s.current_appointment.organ.name
        for s in snapshots
        if s.current_appointment
    }
    words = {word.casefold()[:5] for word in query.split() if len(word) > 3}
    ranked = sorted(
        [
            (len(words & {w.casefold()[:5] for w in name.split() if len(w) > 3}), key)
            for key, name in names.items()
        ],
        reverse=True,
    )
    if not ranked or ranked[0][0] == 0 or (len(ranked) > 1 and ranked[0][0] == ranked[1][0]):
        raise ValueError("ambiguous organ")
    return ranked[0][1]


def _surname_candidates(people: Sequence[Person], query: str) -> Sequence[Person]:
    # A surname mention must not match another official's patronymic (Иванов / Ивановна).
    if " " in query.strip():
        return people
    return [p for p in people if p.full_name.split()[0].casefold().startswith(query.casefold())]
