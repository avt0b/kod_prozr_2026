from collections import defaultdict
from uuid import UUID

from src.core.utils.text import short_name
from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.facts import (
    AppointmentFacts,
    ContractFacts,
    EmploymentFacts,
    OfficialFacts,
)
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

EX_EMPLOYER_YEARS = 3.0


class ExEmployerSupplierRule(RiskRule):
    """R03. Бывший работодатель служащего — подрядчик его органа.

    Срабатывает на контракт, если одновременно:
      * служащий работал в компании до назначения в орган-заказчик;
      * контракт подписан в период назначения;
      * от ухода из компании до контракта прошло не больше 3 лет (data.md: подрядчик через
        5 лет после увольнения — не флаг).
    Один флаг на компанию; полномочия по закупкам не требуются: важна связь с бывшим работодателем.
    """

    code = RuleCode.R03
    name = "ex_employer_supplier"
    severity = Severity.MEDIUM
    legal_ref = "273-ФЗ ст. 10"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        hits: dict[UUID, list[tuple[EmploymentFacts, AppointmentFacts, ContractFacts]]] = (
            defaultdict(list)
        )
        for employment in official.employments:
            if employment.ended_at is None:
                continue
            for appointment in official.appointments:
                if employment.started_at >= appointment.started_at:
                    continue  # работа после назначения — это R04 или R02, не R03
                for contract in world.contracts_between(
                    appointment.organ_id, employment.company_id
                ):
                    if not appointment.contains(contract.signed_at):
                        continue
                    gap = years_between(employment.ended_at, contract.signed_at)
                    if 0 <= gap <= EX_EMPLOYER_YEARS:
                        hits[employment.company_id].append((employment, appointment, contract))

        flags: list[RiskFlag] = []
        for company_id, found in hits.items():
            company = world.company(company_id)
            if company is None:
                continue
            employment, appointment, _ = found[0]
            contracts = list({c.id: c for _, _, c in found}.values())
            name = short_name(official.person.full_name)
            explanation = (
                f"До назначения на должность «{appointment.position_title}» в "
                f"«{appointment.organ_name}» {name} работал(а) в {quoted(company.name)} "
                f"(ИНН {company.inn}) до {employment.ended_at:%d.%m.%Y}. В пределах трёх лет "
                f"после ухода компания получила от органа {contracts_summary(contracts)}. "
                "Это может свидетельствовать о конфликте интересов: требуется проверить, "
                "участвовал(а) ли служащий в выборе поставщика."
            )
            evidence = [
                person_node(official.person),
                company_node(company),
                *contract_nodes(contracts),
                organ_node(appointment.organ_id, appointment.organ_name),
            ]
            flags.append(self.make_flag(official, explanation, evidence))
        return flags
