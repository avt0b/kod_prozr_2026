from collections import defaultdict
from uuid import UUID

from src.core.utils.text import short_name
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import (
    AppointmentFacts,
    CompanyFacts,
    CompanyRoleFacts,
    OfficialFacts,
)
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.rules.base import RiskRule, person_node, quoted
from src.modules.risk.domain.world import RiskWorld

DIRECTOR = "director"


class OwnBusinessRule(RiskRule):
    """R02. Служащий (действующий, на сегодня) — учредитель или руководитель действующей
    коммерческой организации (роль активна на сегодня, статус компании `active`).

    Один флаг на компанию:
      * руководитель (с долей или без) — high: прямой запрет, 79-ФЗ ст. 17 ч. 1 п. 3;
      * только учредитель — medium: владение долей само по себе не запрещено, но доля должна
        быть передана в доверительное управление (ст. 17 ч. 3.1). Решение T-01 (contracts.md).
    Ликвидированные и ликвидируемые компании, роли в прошлом и бизнес родственников не считаются.
    """

    code = RuleCode.R02
    name = "own_business"
    severity = Severity.HIGH
    legal_ref = "79-ФЗ ст. 17"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        active = official.active_appointments(world.today)
        if not active:
            return []
        appointment = max(active, key=lambda a: a.started_at)

        roles_by_company: dict[UUID, list[CompanyRoleFacts]] = defaultdict(list)
        for role in world.roles_of(official.person.id):
            if role.active_on(world.today):
                roles_by_company[role.company_id].append(role)

        flags: list[RiskFlag] = []
        for company_id, roles in roles_by_company.items():
            company = world.company(company_id)
            if company is None or not company.is_active:
                continue
            flags.append(self._flag(official, appointment, company, roles))
        return flags

    def _flag(
        self,
        official: OfficialFacts,
        appointment: AppointmentFacts,
        company: CompanyFacts,
        roles: list[CompanyRoleFacts],
    ) -> RiskFlag:
        name = short_name(official.person.full_name)
        director = next((r for r in roles if r.role == DIRECTOR), None)
        founder = next((r for r in roles if r.role != DIRECTOR), None)
        share = f" с долей {founder.share:g}%" if founder and founder.share is not None else ""
        since = min(r.started_at for r in roles)
        position = (
            f"одновременно замещая должность «{appointment.position_title}» "
            f"в «{appointment.organ_name}»"
        )
        company_ref = f"{quoted(company.name)} (ИНН {company.inn})"

        if director is not None:
            founder_part = f" и учредителем{share}" if founder else ""
            explanation = (
                f"{name} является руководителем{founder_part} действующей коммерческой "
                f"организации {company_ref} с {since:%d.%m.%Y}, {position}. Это может "
                "свидетельствовать о нарушении запрета участвовать в управлении коммерческой "
                "организацией."
            )
            severity = Severity.HIGH
        else:
            explanation = (
                f"{name} является учредителем{share} действующей коммерческой организации "
                f"{company_ref} с {since:%d.%m.%Y}, {position}. Владение долей само по себе "
                "не запрещено: требуется проверить, передана ли доля в доверительное управление."
            )
            severity = Severity.MEDIUM

        evidence = [
            person_node(official.person),
            EvidenceNode(type=NodeType.COMPANY, id=company.id, label=company.name),
            EvidenceNode(
                type=NodeType.ORGAN, id=appointment.organ_id, label=appointment.organ_name
            ),
        ]
        return self.make_flag(official, explanation, evidence, severity=severity)
