from src.modules.risk.domain.rules.base import RiskRule
from src.modules.risk.domain.rules.r01_relative_supplier import RelativeSupplierRule
from src.modules.risk.domain.rules.r02_own_business import OwnBusinessRule
from src.modules.risk.domain.rules.r07_appeal_mentions import AppealMentionsRule
from src.modules.risk.domain.rules.stubs import (
    ExEmployerSupplierRule,
    PeerAnomalyRule,
    RevolvingDoorRule,
    SharedContactsRule,
    SupplierConcentrationRule,
)
from src.modules.risk.domain.score import ScorePolicy


def default_rules(policy: ScorePolicy | None = None) -> list[RiskRule]:
    """Набор правил движка. Новое правило добавляется сюда."""
    return [
        RelativeSupplierRule(policy),
        OwnBusinessRule(policy),
        ExEmployerSupplierRule(policy),
        RevolvingDoorRule(policy),
        SharedContactsRule(policy),
        SupplierConcentrationRule(policy),
        AppealMentionsRule(policy),
        PeerAnomalyRule(policy),
    ]


__all__ = ["RiskRule", "default_rules"]
