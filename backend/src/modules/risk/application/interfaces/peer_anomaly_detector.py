from typing import Protocol

from src.modules.risk.domain.facts import PeerAnomalyFacts
from src.modules.risk.domain.world import RiskWorld


class PeerAnomalyDetectorInterface(Protocol):
    """ML-детектор R08 (ai.md §4, задача AI-07).

    Получает весь снимок (служащие, должности, контракты, компании) и возвращает служащих,
    аномальных относительно коллег, с признаками для объяснения. Вызывается только при полном
    пересчёте: на подмножестве служащих группа коллег неполная.
    Реализация — risk/infrastructure/ml/, по умолчанию NoPeerAnomalyDetector.
    """

    def detect(self, world: RiskWorld) -> list[PeerAnomalyFacts]: ...
