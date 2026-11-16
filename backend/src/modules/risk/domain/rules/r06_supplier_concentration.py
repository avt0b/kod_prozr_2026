from collections import defaultdict
from uuid import UUID

from src.core.utils.text import format_rub, short_name
from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.facts import (
    PROCUREMENT,
    AppointmentFacts,
    CompanyFacts,
    ContractFacts,
    OfficialFacts,
)
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.base import (
    RiskRule,
    company_node,
    contract_nodes,
    organ_node,
    person_node,
    plural_contracts,
    quoted,
)
from src.modules.risk.domain.world import RiskWorld

# Стартовые пороги (B-15), калибруются на синтетике (B-17).
SHARE_THRESHOLD = 0.5  # доля одного поставщика по сумме
MIN_CONTRACTS = 4  # меньше контрактов в сфере — доля ничего не говорит


class SupplierConcentrationRule(RiskRule):
    """R06. Аномальная доля одного поставщика в закупках в сфере полномочий служащего.

    Сфера — коды ОКПД2 полномочия procurement (пустая сфера — правило не применяется: доля
    по всему органу не связана с полномочиями служащего). Берутся контракты органа по этим
    кодам, подписанные в период назначения. Если на одного поставщика приходится больше
    SHARE_THRESHOLD суммы — флаг low. Сам по себе он не говорит о нарушении (бывает
    единственный производитель), но усиливает другие флаги на ту же компанию.
    """

    code = RuleCode.R06
    name = "supplier_concentration"
    severity = Severity.LOW
    legal_ref = None

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        flags: list[RiskFlag] = []
        seen: set[tuple[UUID, str, UUID]] = set()
        for appointment in official.appointments:
            for authority in appointment.authorities_of(PROCUREMENT):
                for prefix in authority.okpd2:
                    contracts = [
                        c
                        for c in world.contracts_of_organ(appointment.organ_id)
                        if c.okpd2 is not None
                        and c.okpd2.startswith(prefix)
                        and appointment.contains(c.signed_at)
                    ]
                    if len(contracts) < MIN_CONTRACTS:
                        continue
                    found = self._dominant(contracts)
                    if found is None:
                        continue
                    company_id, share = found
                    company = world.company(company_id)
                    key = (appointment.organ_id, prefix, company_id)
                    if company is None or key in seen:
                        continue
                    seen.add(key)
                    flags.append(
                        self._flag(official, appointment, prefix, company, share, contracts)
                    )
        return flags

    @staticmethod
    def _dominant(contracts: list[ContractFacts]) -> tuple[UUID, float] | None:
        total = sum(c.amount for c in contracts)
        if total <= 0:
            return None
        by_supplier: dict[UUID, float] = defaultdict(float)
        for contract in contracts:
            by_supplier[contract.supplier_company_id] += contract.amount
        company_id, amount = max(by_supplier.items(), key=lambda item: item[1])
        share = amount / total
        return (company_id, share) if share > SHARE_THRESHOLD else None

    def _flag(
        self,
        official: OfficialFacts,
        appointment: AppointmentFacts,
        prefix: str,
        company: CompanyFacts,
        share: float,
        contracts: list[ContractFacts],
    ) -> RiskFlag:
        own = [c for c in contracts if c.supplier_company_id == company.id]
        total = sum(c.amount for c in contracts)
        name = short_name(official.person.full_name)
        explanation = (
            f"В закупках «{appointment.organ_name}» по ОКПД2 {prefix} — сфере полномочий "
            f"{name} — на {quoted(company.name)} (ИНН {company.inn}) приходится "
            f"{share:.0%} суммы: {len(own)} {plural_contracts(len(own))} из {len(contracts)} "
            f"на {format_rub(sum(c.amount for c in own))} из {format_rub(total)}. "
            "Высокая доля одного поставщика может свидетельствовать об ограничении конкуренции; "
            "бывает и объективной (единственный производитель), поэтому вес флага низкий."
        )
        evidence = [
            person_node(official.person),
            organ_node(appointment.organ_id, appointment.organ_name),
            company_node(company),
            *contract_nodes(own),
        ]
        return self.make_flag(official, explanation, evidence)
