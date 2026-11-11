from src.core.utils.text import short_name
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import OfficialFacts
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.rules.base import RiskRule, person_node, quoted
from src.modules.risk.domain.world import RiskWorld


class OwnBusinessRule(RiskRule):
    """R02. Служащий (действующий, на сегодня) — учредитель или руководитель действующей
    коммерческой организации (роль активна на сегодня, статус компании `active`).

    Руководство — прямой запрет (79-ФЗ ст. 17 ч. 1 п. 3). Участие в капитале само по себе
    не запрещено, но доля должна быть передана в доверительное управление (ст. 17 ч. 3.1),
    поэтому флаг ставится в обоих случаях с разным текстом объяснения.
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
        name = short_name(official.person.full_name)

        flags: list[RiskFlag] = []
        for role in world.roles_of(official.person.id):
            company = world.company(role.company_id)
            if company is None or not company.is_active or not role.active_on(world.today):
                continue
            if role.role == "director":
                essence = (
                    f"{name} является руководителем действующей коммерческой организации "
                    f"{quoted(company.name)} (ИНН {company.inn}) с {role.started_at:%d.%m.%Y}, "
                    f"одновременно замещая должность «{appointment.position_title}» "
                    f"в «{appointment.organ_name}». Служащему запрещено участвовать в "
                    "управлении коммерческой организацией."
                )
            else:
                share = f" с долей {role.share:g}%" if role.share is not None else ""
                essence = (
                    f"{name} является учредителем{share} действующей коммерческой организации "
                    f"{quoted(company.name)} (ИНН {company.inn}) с {role.started_at:%d.%m.%Y}, "
                    f"одновременно замещая должность «{appointment.position_title}» "
                    f"в «{appointment.organ_name}». Требуется проверить передачу доли "
                    "в доверительное управление."
                )
            evidence = [
                person_node(official.person),
                EvidenceNode(type=NodeType.COMPANY, id=company.id, label=company.name),
                EvidenceNode(
                    type=NodeType.ORGAN, id=appointment.organ_id, label=appointment.organ_name
                ),
            ]
            flags.append(self.make_flag(official, essence, evidence))
        return flags
