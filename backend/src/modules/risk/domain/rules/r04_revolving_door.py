from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.core.utils.text import short_name
from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.facts import AppointmentFacts, ContractFacts, OfficialFacts
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.base import (
    RiskRule,
    company_node,
    contract_nodes,
    contracts_summary,
    organ_node,
    person_node,
    quoted,
    years_between,
)
from src.modules.risk.domain.world import RiskWorld

REVOLVING_DOOR_YEARS = 2.0  # 273-ФЗ ст. 12: два года после увольнения
ROLE_LABELS = {"founder": "учредителем", "director": "руководителем"}


@dataclass(frozen=True)
class _Move:
    company_id: UUID
    started_at: date
    what: str


class RevolvingDoorRule(RiskRule):
    """R04. После увольнения служащий перешёл в компанию, которая была в сфере его полномочий.

    Срабатывает, если одновременно:
      * назначение завершено (ended_at задан) и у должности были полномочия;
      * в течение 2 лет после увольнения служащий начал работать в компании или стал её
        учредителем или руководителем;
      * компания получала контракты органа в период этого назначения.
    """

    code = RuleCode.R04
    name = "revolving_door"
    severity = Severity.MEDIUM
    legal_ref = "273-ФЗ ст. 12"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        moves = [_Move(e.company_id, e.started_at, "работает") for e in official.employments]
        moves += [
            _Move(r.company_id, r.started_at, f"стал(а) {ROLE_LABELS.get(r.role, r.role)}")
            for r in world.roles_of(official.person.id)
        ]

        flags: list[RiskFlag] = []
        seen: set[UUID] = set()
        for appointment in official.appointments:
            if appointment.ended_at is None or not appointment.authorities:
                continue
            for move in sorted(moves, key=lambda m: m.started_at):
                if move.company_id in seen:
                    continue
                gap = years_between(appointment.ended_at, move.started_at)
                if not 0 <= gap <= REVOLVING_DOOR_YEARS:
                    continue
                contracts = [
                    c
                    for c in world.contracts_between(appointment.organ_id, move.company_id)
                    if appointment.contains(c.signed_at)
                ]
                if contracts:
                    seen.add(move.company_id)
                    flag = self._flag(official, appointment, move, contracts, world)
                    if flag is not None:
                        flags.append(flag)
        return flags

    def _flag(
        self,
        official: OfficialFacts,
        appointment: AppointmentFacts,
        move: _Move,
        contracts: list[ContractFacts],
        world: RiskWorld,
    ) -> RiskFlag | None:
        company = world.company(move.company_id)
        if company is None or appointment.ended_at is None:
            return None
        name = short_name(official.person.full_name)
        explanation = (
            f"{name} замещал(а) должность «{appointment.position_title}» в "
            f"«{appointment.organ_name}» до {appointment.ended_at:%d.%m.%Y}. "
            f"С {move.started_at:%d.%m.%Y} {move.what} в {quoted(company.name)} "
            f"(ИНН {company.inn}), которая в период его (её) полномочий получила от органа "
            f"{contracts_summary(contracts)}. Это может свидетельствовать о нарушении "
            "ограничений после увольнения: требуется проверить согласие комиссии по "
            "урегулированию конфликта интересов."
        )
        evidence = [
            person_node(official.person),
            company_node(company),
            *contract_nodes(contracts),
            organ_node(appointment.organ_id, appointment.organ_name),
        ]
        return self.make_flag(official, explanation, evidence)
