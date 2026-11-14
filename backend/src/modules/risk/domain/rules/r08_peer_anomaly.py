from src.core.utils.text import short_name
from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.facts import FeatureDeviation, OfficialFacts
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.base import RiskRule, organ_node, person_node
from src.modules.risk.domain.world import RiskWorld

TOP_FEATURES = 3


class PeerAnomalyRule(RiskRule):
    """R08. Аномалия относительно коллег той же должности и региона (ML, ai.md §4).

    Само правило ничего не считает: оценки даёт детектор за портом
    PeerAnomalyDetectorInterface (адаптер в risk/infrastructure/ml/), и RecomputeRiskUseCase
    кладёт их в снимок. Правило превращает оценку во флаг с объяснением по трём признакам с
    наибольшим |z|. Вес R08 ограничен (5 / 10, ScorePolicy): ML один не выводит в топ.
    """

    code = RuleCode.R08
    name = "peer_anomaly"
    severity = Severity.LOW
    legal_ref = None

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        anomaly = world.peer_anomaly_of(official.person.id)
        if anomaly is None or not anomaly.features:
            return []
        top = sorted(anomaly.features, key=lambda f: abs(f.z), reverse=True)[:TOP_FEATURES]
        details = "; ".join(_describe(f) for f in top)
        explanation = (
            f"Показатели {short_name(official.person.full_name)} нетипичны для коллег "
            f"(группа сравнения — {anomaly.peers_count} чел. со схожими полномочиями в регионе): "
            f"{details}. "
            "Это статистическая аномалия, а не нарушение: она подсказывает, куда посмотреть."
        )
        evidence = [person_node(official.person)]
        active = official.active_appointments(world.today) or official.appointments
        if active:
            current = max(active, key=lambda a: a.started_at)
            evidence.append(organ_node(current.organ_id, current.organ_name))
        severity = Severity.MEDIUM if anomaly.severity == Severity.MEDIUM else Severity.LOW
        return [self.make_flag(official, explanation, evidence, severity=severity)]


def _describe(feature: FeatureDeviation) -> str:
    if feature.is_share:
        return f"{feature.label} — {feature.value:.0%} при медиане коллег {feature.peer_median:.0%}"
    return f"{feature.label} — {feature.value:g} при медиане коллег {feature.peer_median:g}"
