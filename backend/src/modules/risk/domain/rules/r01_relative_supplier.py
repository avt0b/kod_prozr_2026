from datetime import date

from src.core.utils.text import format_rub, short_name
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import (
    PROCUREMENT,
    AppointmentFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
    PersonFacts,
)
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.rules.base import RiskRule, person_node, quoted
from src.modules.risk.domain.world import RiskWorld

MAX_EVIDENCE_CONTRACTS = 5


class RelativeSupplierRule(RiskRule):
    """R01. Служащий или его родственник — учредитель/руководитель компании, которая получает
    контракты органа, где у служащего полномочия `procurement`.

    Срабатывает на контракт, если одновременно:
      * контракт заключён органом, где служащий в момент подписания занимал должность
        с полномочием procurement;
      * код ОКПД2 контракта входит в сферу этого полномочия (пустая сфера = любые коды);
      * в момент подписания служащий/родственник был учредителем или руководителем поставщика.
    Один флаг на пару (связанное лицо, компания); контракты перечислены в объяснении.
    """

    code = RuleCode.R01
    name = "relative_supplier"
    severity = Severity.HIGH
    legal_ref = "273-ФЗ ст. 10, 11"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        procurement = [a for a in official.appointments if a.authorities_of(PROCUREMENT)]
        if not procurement:
            return []

        linked: list[tuple[PersonFacts, str | None]] = [(official.person, None)]
        linked += [(r.person, r.kind_label) for r in official.relatives]

        flags: list[RiskFlag] = []
        for person, kinship_label in linked:
            for role in world.roles_of(person.id):
                company = world.company(role.company_id)
                if company is None:
                    continue
                hits = self._matching_contracts(procurement, role, company, world)
                if hits:
                    flags.append(self._flag(official, person, kinship_label, role, company, hits))
        return flags

    @staticmethod
    def _matching_contracts(
        appointments: list[AppointmentFacts],
        role: CompanyRoleFacts,
        company: CompanyFacts,
        world: RiskWorld,
    ) -> list[tuple[AppointmentFacts, ContractFacts]]:
        hits: list[tuple[AppointmentFacts, ContractFacts]] = []
        seen: set[object] = set()
        for appointment in appointments:
            authorities = appointment.authorities_of(PROCUREMENT)
            for contract in world.contracts_between(appointment.organ_id, company.id):
                if contract.id in seen:
                    continue
                signed: date = contract.signed_at
                if not appointment.contains(signed) or not role.active_on(signed):
                    continue
                if not any(a.covers_okpd2(contract.okpd2) for a in authorities):
                    continue
                seen.add(contract.id)
                hits.append((appointment, contract))
        return sorted(hits, key=lambda hit: hit[1].signed_at)

    def _flag(
        self,
        official: OfficialFacts,
        person: PersonFacts,
        kinship_label: str | None,
        role: CompanyRoleFacts,
        company: CompanyFacts,
        hits: list[tuple[AppointmentFacts, ContractFacts]],
    ) -> RiskFlag:
        appointment = hits[0][0]
        contracts = [contract for _, contract in hits]
        total = sum(c.amount for c in contracts)
        share = f" (доля {role.share:g}%)" if role.share is not None else ""
        official_name = short_name(official.person.full_name)
        subject = (
            official_name
            if kinship_label is None
            else f"{short_name(person.full_name)} ({kinship_label} служащего: {official_name})"
        )
        explanation = (
            f"{subject} является "
            f"{_role_instrumental(role.role)}{share} компании {quoted(company.name)} "
            f"(ИНН {company.inn}). Компания получила {len(contracts)} "
            f"{_plural_contracts(len(contracts))} от «{appointment.organ_name}» "
            f"на {format_rub(total)}, когда {official_name} занимал(а) "
            f"должность «{appointment.position_title}» с полномочиями по закупкам. "
            "Возможен конфликт интересов: требуется проверка уведомления о личной "
            "заинтересованности и самоотвода."
        )

        evidence: list[EvidenceNode] = [person_node(official.person)]
        if kinship_label is not None:
            evidence.append(person_node(person))
        evidence.append(EvidenceNode(type=NodeType.COMPANY, id=company.id, label=company.name))
        for contract in contracts[:MAX_EVIDENCE_CONTRACTS]:
            evidence.append(
                EvidenceNode(
                    type=NodeType.CONTRACT,
                    id=contract.id,
                    label=f"№{contract.reg_number} от {contract.signed_at:%d.%m.%Y}, "
                    f"{format_rub(contract.amount)}",
                )
            )
        evidence.append(
            EvidenceNode(type=NodeType.ORGAN, id=appointment.organ_id, label=appointment.organ_name)
        )
        return self.make_flag(official, explanation, evidence)


def _role_instrumental(role: str) -> str:
    return {"founder": "учредителем", "director": "руководителем"}.get(role, role)


def _plural_contracts(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "контракт"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "контракта"
    return "контрактов"
