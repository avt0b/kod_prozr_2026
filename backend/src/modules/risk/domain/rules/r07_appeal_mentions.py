from src.core.utils.text import short_name
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import AppealMentionFacts, OfficialFacts
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.rules.base import RiskRule, person_node
from src.modules.risk.domain.world import RiskWorld

# Пороги из docs/ai.md (ADR-10): s = Σ confidence_i · specificity_i
MEDIUM_THRESHOLD = 0.8
HIGH_THRESHOLD = 1.6
MAX_EVIDENCE_APPEALS = 10

CATEGORY_LABELS = {
    "bribe": "взятка",
    "conflict_of_interest": "конфликт интересов",
    "procurement": "закупки",
    "abuse_of_power": "превышение полномочий",
    "other": "другое",
}


class AppealMentionsRule(RiskRule):
    """R07. Служащий упомянут в обращениях с признаками коррупции.

    Учитываются привязанные обращения с is_corruption = true.
    s = Σ confidence · specificity; s < 0.8 -> low, 0.8 ≤ s < 1.6 -> medium, s ≥ 1.6 -> high.
    Одно расплывчатое обращение даёт только low: ложный донос не выводит служащего в топ.

    TODO: дедупликация «один заявитель / дубль текста» (в Appeal пока нет заявителя).
    """

    code = RuleCode.R07
    name = "appeal_mentions"
    severity = Severity.LOW
    legal_ref = None

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        mentions = [m for m in world.mentions_of(official.person.id) if m.is_corruption]
        if not mentions:
            return []
        unique = list({m.appeal_id: m for m in mentions}.values())
        unique.sort(key=lambda m: m.received_at, reverse=True)

        s = sum(m.confidence * m.specificity for m in unique)
        level = self.severity_for(s)
        name = short_name(official.person.full_name)
        details = "; ".join(_describe(m) for m in unique[:MAX_EVIDENCE_APPEALS])
        explanation = (
            f"{name} упоминается в {len(unique)} {_plural_appeals(len(unique))} с признаками "
            f"коррупции (суммарная конкретность {s:.2f}): {details}. "
            "Сведения из обращений требуют проверки и сами по себе не подтверждают нарушение."
        )
        evidence = [person_node(official.person)] + [
            EvidenceNode(
                type=NodeType.APPEAL,
                id=m.appeal_id,
                label=f"Обращение от {m.received_at:%d.%m.%Y}",
            )
            for m in unique[:MAX_EVIDENCE_APPEALS]
        ]
        return [self.make_flag(official, explanation, evidence, severity=level)]

    @staticmethod
    def severity_for(s: float) -> Severity:
        if s >= HIGH_THRESHOLD:
            return Severity.HIGH
        if s >= MEDIUM_THRESHOLD:
            return Severity.MEDIUM
        return Severity.LOW


def _describe(mention: AppealMentionFacts) -> str:
    category = CATEGORY_LABELS.get(mention.category or "", "без категории")
    text = f"{mention.received_at:%d.%m.%Y} — {category}"
    if mention.summary:
        text += f" ({mention.summary[:120]})"
    return text


def _plural_appeals(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "обращении"
    return "обращениях"
